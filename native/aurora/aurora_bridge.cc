// aurora_bridge: stream Aurora 930 RGB + aligned depth to stdout for the Osprey ground processor.
// Usage: aurora_bridge [mode_index=2] [jpeg_quality=80] [flip=0]
// Each frame on stdout: uint32 LE header_len | header JSON | BGR8 (w*h*3) | depth uint16 LE (w*h*2).
// Header: {"seq","ts_ms","w","h","fx","fy","cx","cy","bgr_len","depth_len","temp"}.
// Logs go to stderr. Exits non-zero on device errors so the parent can restart it.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>
#include <vector>

#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

#include "deptrum/aurora900_series.h"
#include "deptrum/device.h"
#include "deptrum/stream.h"

using namespace deptrum;
using namespace deptrum::stream;

static bool WriteAll(const void* p, size_t n) {
  const char* c = (const char*)p;
  while (n) {
    size_t w = fwrite(c, 1, n, stdout);
    if (w == 0) return false;
    c += w; n -= w;
  }
  return true;
}

int main(int argc, char** argv) {
  int mode_index = argc > 1 ? std::atoi(argv[1]) : 2;
  int quality = argc > 2 ? std::atoi(argv[2]) : 80;
  bool flip = argc > 3 && std::atoi(argv[3]) != 0;

  DeviceManager::GetInstance()->RegisterDeviceConnectedCallback();
  std::vector<DeviceInformation> devs;
  int ret = DeviceManager::GetInstance()->GetDeviceList(devs);
  if (ret != 0 || devs.empty()) { fprintf(stderr, "no device (ret=%d)\n", ret); return 2; }
  auto device = DeviceManager::GetInstance()->CreateDevice(devs[0]);
  if (!device || device->Open() != 0) { fprintf(stderr, "open failed\n"); return 2; }

  std::vector<std::tuple<FrameMode, FrameMode, FrameMode>> modes;
  device->GetSupportedFrameMode(modes);
  if (mode_index < 0 || mode_index >= (int)modes.size()) { fprintf(stderr, "bad mode\n"); return 2; }
  auto& m = modes[mode_index];
  if (device->SetMode(std::get<0>(m), std::get<1>(m), std::get<2>(m)) != 0) {
    fprintf(stderr, "SetMode failed\n"); return 2;
  }
  auto aurora = std::dynamic_pointer_cast<Aurora900>(device);
  if (aurora) {
    aurora->SetIrFps(15);
    aurora->SwitchAlignedMode(true);
    aurora->DepthCorrection(true);
    HeartbeatParam hb;
    hb.allowable_failures_counts = 8; hb.timeout = 500; hb.is_enabled = true;
    aurora->SetHeartbeat(hb, [](int flag) {
      if (flag != 1) { fprintf(stderr, "heartbeat lost (%d), exiting\n", flag); fflush(stderr); std::_Exit(3); }
    });
  }
  Intrinsic ir_k, rgb_k; Extrinsic ext;
  float fx = 424, fy = 425, cx = 320, cy = 198;
  if (device->GetCameraParameters(ir_k, rgb_k, ext) == 0) {
    // aligned mode maps depth onto the RGB image, so use RGB intrinsics
    fx = rgb_k.focal_length[0]; fy = rgb_k.focal_length[1];
    cx = rgb_k.principal_point[0]; cy = rgb_k.principal_point[1];
  }
  Stream* stream = nullptr;
  // kRgbdIr is the combination verified by aurora_probe (kRgbd alone delivered no frames)
  std::vector<StreamType> types{kRgbdIr};
  if (device->CreateStream(stream, types) != 0 || stream->Start() != 0) {
    fprintf(stderr, "stream start failed\n"); return 2;
  }
  fprintf(stderr, "aurora_bridge streaming mode %d fx=%.1f fy=%.1f cx=%.1f cy=%.1f flip=%d\n",
          mode_index, fx, fy, cx, cy, flip);

  (void)quality;
  long seq = 0;
  int failures = 0;
  while (true) {
    StreamFrames frames;
    int gr = stream->GetFrames(frames, 2000);
    if (seq < 2) fprintf(stderr, "GetFrames ret=%d n=%zu\n", gr, frames.frame_ptr.size());
    if (gr != 0) {
      if (++failures > 5) { fprintf(stderr, "too many GetFrames failures\n"); return 3; }
      continue;
    }
    failures = 0;
    auto now = std::chrono::system_clock::now();
    double ts_ms = std::chrono::duration<double, std::milli>(now.time_since_epoch()).count();
    cv::Mat bgr, depth;
    float temp = 0;
    for (auto& fp : frames.frame_ptr) {
      void* p = fp->data.get();
      if (fp->frame_type == kRgbFrame) {
        if (fp->image_format == kJpeg) {
          std::vector<uchar> buf((uchar*)p, (uchar*)p + fp->size);
          bgr = cv::imdecode(buf, cv::IMREAD_COLOR);
        } else if (fp->bits_per_pixel == 12) {
          cv::Mat yuv(fp->rows * 3 / 2, fp->cols, CV_8UC1, p);
          cv::cvtColor(yuv, bgr, cv::COLOR_YUV2BGR_NV12);
        } else if (fp->bits_per_pixel == 24) {
          bgr = cv::Mat(fp->rows, fp->cols, CV_8UC3, p).clone();
        }
        temp = fp->temperature;
      } else if (fp->frame_type == kDepthFrame && fp->bits_per_pixel == 16) {
        depth = cv::Mat(fp->rows, fp->cols, CV_16UC1, p).clone();
      }
    }
    if (bgr.empty()) {
      if (seq < 2) fprintf(stderr, "no rgb in frame set\n");
      continue;
    }
    if (flip) {
      cv::rotate(bgr, bgr, cv::ROTATE_180);
      if (!depth.empty()) cv::rotate(depth, depth, cv::ROTATE_180);
    }
    if (!depth.empty() && depth.size() != bgr.size()) {
      cv::resize(depth, depth, bgr.size(), 0, 0, cv::INTER_NEAREST);
    }
    // Raw BGR: cv::imencode(".jpg") segfaults in this process (libjpeg clash with the Deptrum
    // SDK), so the Python side encodes JPEG.
    if (!bgr.isContinuous()) bgr = bgr.clone();
    size_t bgr_len = bgr.total() * 3;
    size_t depth_len = depth.empty() ? 0 : depth.total() * 2;
    char header[512];
    int n = snprintf(header, sizeof(header),
                     "{\"seq\":%ld,\"ts_ms\":%.1f,\"w\":%d,\"h\":%d,\"fx\":%.2f,\"fy\":%.2f,\"cx\":%.2f,"
                     "\"cy\":%.2f,\"bgr_len\":%zu,\"depth_len\":%zu,\"temp\":%.1f}",
                     ++seq, ts_ms, bgr.cols, bgr.rows, fx, fy, cx, cy, bgr_len, depth_len, temp);
    uint32_t len = (uint32_t)n;
    if (!WriteAll(&len, 4) || !WriteAll(header, n) || !WriteAll(bgr.data, bgr_len)) return 4;
    if (depth_len && !WriteAll(depth.data, depth_len)) return 4;
    fflush(stdout);
  }
}
