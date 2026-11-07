// aurora_probe: non-interactive Aurora 930 sanity check.
// Usage: aurora_probe [mode_index=0] [ir_fps=10] [n_frames=60] [out_dir=.]
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <iostream>
#include <map>
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

static const char* FrameTypeName(FrameType t) {
  switch (t) {
    case kRgbFrame: return "rgb";
    case kIrFrame: return "ir";
    case kDepthFrame: return "depth";
    case kLaserFrame: return "laser";
    case kPointCloudFrame: return "pointcloud";
    default: return "other";
  }
}

static cv::Mat ToMat(const StreamFrame& f) {
  void* p = f.data.get();
  if (f.image_format == kJpeg) {
    std::vector<uchar> buf((uchar*)p, (uchar*)p + f.size);
    return cv::imdecode(buf, cv::IMREAD_COLOR);
  }
  if (f.bits_per_pixel == 12) {  // NV12: Y plane + interleaved UV at half res
    cv::Mat yuv(f.rows * 3 / 2, f.cols, CV_8UC1, p), bgr;
    cv::cvtColor(yuv, bgr, cv::COLOR_YUV2BGR_NV12);
    return bgr;
  }
  int type = f.bits_per_pixel == 16 ? CV_16UC1 : f.bits_per_pixel == 24 ? CV_8UC3 : CV_8UC1;
  return cv::Mat(f.rows, f.cols, type, p).clone();
}

int main(int argc, char** argv) {
  int mode_index = argc > 1 ? std::atoi(argv[1]) : 0;
  int ir_fps = argc > 2 ? std::atoi(argv[2]) : 10;
  int n_frames = argc > 3 ? std::atoi(argv[3]) : 60;
  std::string out_dir = argc > 4 ? argv[4] : ".";

  DeviceManager::GetInstance()->RegisterDeviceConnectedCallback();
  std::vector<DeviceInformation> devs;
  int ret = DeviceManager::GetInstance()->GetDeviceList(devs);
  if (ret != 0 || devs.empty()) { printf("FAIL no device (ret=%d)\n", ret); return 1; }

  auto device = DeviceManager::GetInstance()->CreateDevice(devs[0]);
  if (!device) { printf("FAIL CreateDevice\n"); return 1; }
  if ((ret = device->Open()) != 0) { printf("FAIL Open ret=%d\n", ret); return 1; }
  printf("device=%s sdk=%s\n", device->GetDeviceName().c_str(), device->GetSdkVersion().c_str());

  std::vector<std::tuple<FrameMode, FrameMode, FrameMode>> modes;
  device->GetSupportedFrameMode(modes);
  printf("supported modes (ir, rgb, depth enum ids):\n");
  for (size_t i = 0; i < modes.size(); i++)
    printf("  [%zu] %d %d %d\n", i, std::get<0>(modes[i]), std::get<1>(modes[i]), std::get<2>(modes[i]));
  if (mode_index < 0 || mode_index >= (int)modes.size()) { printf("FAIL bad mode index\n"); return 1; }
  auto& m = modes[mode_index];
  if ((ret = device->SetMode(std::get<0>(m), std::get<1>(m), std::get<2>(m))) != 0) {
    printf("FAIL SetMode ret=%d\n", ret); return 1;
  }

  auto aurora = std::dynamic_pointer_cast<Aurora900>(device);
  if (aurora) {
    printf("SetIrFps(%d) ret=%d\n", ir_fps, aurora->SetIrFps(ir_fps));
    printf("SwitchAlignedMode(true) ret=%d\n", aurora->SwitchAlignedMode(true));
    aurora->DepthCorrection(true);
    HeartbeatParam hb;
    hb.allowable_failures_counts = 8; hb.timeout = 500; hb.is_enabled = true;
    aurora->SetHeartbeat(hb, [](int flag) { if (flag != 1) printf("heartbeat: %d\n", flag); });
  }

  Intrinsic ir_k, rgb_k; Extrinsic ext;
  if (device->GetCameraParameters(ir_k, rgb_k, ext) == 0) {
    printf("ir  intrinsics %dx%d fx=%.1f fy=%.1f cx=%.1f cy=%.1f\n", ir_k.cols, ir_k.rows,
           ir_k.focal_length[0], ir_k.focal_length[1], ir_k.principal_point[0], ir_k.principal_point[1]);
    printf("rgb intrinsics %dx%d fx=%.1f fy=%.1f cx=%.1f cy=%.1f\n", rgb_k.cols, rgb_k.rows,
           rgb_k.focal_length[0], rgb_k.focal_length[1], rgb_k.principal_point[0], rgb_k.principal_point[1]);
  }

  Stream* stream = nullptr;
  std::vector<StreamType> types{kRgbdIr};
  if ((ret = device->CreateStream(stream, types)) != 0) { printf("FAIL CreateStream ret=%d\n", ret); return 1; }
  if ((ret = stream->Start()) != 0) { printf("FAIL Start ret=%d\n", ret); return 1; }

  std::map<std::string, int> counts;
  std::map<std::string, cv::Mat> last;
  bool described = false;
  int got = 0, timeouts = 0;
  auto t0 = std::chrono::steady_clock::now();
  for (int i = 0; i < n_frames; i++) {
    StreamFrames frames;
    ret = stream->GetFrames(frames, 2000);
    if (ret != 0) { timeouts++; if (timeouts > 5) break; continue; }
    got++;
    for (auto& fp : frames.frame_ptr) {
      std::string name = FrameTypeName(fp->frame_type);
      counts[name]++;
      if (!described)
        printf("  frame %-6s %dx%d bpp=%d fmt=%d size=%d temp=%.1fC\n", name.c_str(), fp->cols,
               fp->rows, fp->bits_per_pixel, fp->image_format, fp->size, fp->temperature);
      if (i == n_frames - 1 || i % 10 == 0) last[name] = ToMat(*fp);
    }
    described = true;
  }
  double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  stream->Stop();
  device->DestroyStream(stream);

  printf("frames=%d timeouts=%d elapsed=%.2fs fps=%.2f\n", got, timeouts, secs, got / secs);
  for (auto& kv : counts) printf("  %s: %d\n", kv.first.c_str(), kv.second);

  for (auto& kv : last) {
    if (kv.second.empty()) continue;
    std::string path = out_dir + "/aurora_" + kv.first + ".png";
    cv::imwrite(path, kv.second);
    printf("saved %s\n", path.c_str());
    if (kv.first == "depth" && kv.second.type() == CV_16UC1) {
      cv::Mat d = kv.second;
      std::vector<uint16_t> v;
      for (int r = 0; r < d.rows; r++)
        for (int c = 0; c < d.cols; c++) { uint16_t z = d.at<uint16_t>(r, c); if (z) v.push_back(z); }
      uint16_t center = d.at<uint16_t>(d.rows / 2, d.cols / 2);
      if (!v.empty()) {
        std::sort(v.begin(), v.end());
        printf("depth valid=%.1f%% min=%u median=%u max=%u center=%u (units: likely mm)\n",
               100.0 * v.size() / d.total(), v.front(), v[v.size() / 2], v.back(), center);
      } else {
        printf("depth: no valid pixels\n");
      }
      cv::Mat vis;
      d.convertTo(vis, CV_8U, 255.0 / 3000.0);
      cv::applyColorMap(vis, vis, cv::COLORMAP_JET);
      cv::imwrite(out_dir + "/aurora_depth_vis.png", vis);
    }
  }
  device->Close();
  printf("%s\n", got > 0 ? "PASS" : "FAIL no frames");
  return got > 0 ? 0 : 1;
}
