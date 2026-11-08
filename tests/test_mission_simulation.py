"""Behavioral checks for the dispersed search and uninterrupted rescue story."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
spec=importlib.util.spec_from_file_location('mission_builder',Path(__file__).resolve().parents[1]/'simulation/tools/build_story.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
@pytest.fixture(scope='module')
def story(): return builder.build()

def test_contact_is_continuous_after_lock_and_story_ends_at_rendezvous(story):
    f=story['frames']
    assert all(not x['observed'] for x in f[:builder.LOCK])
    assert all(x['observed'] and not x['rough'] for x in f[builder.LOCK:])
    assert np.linalg.norm(np.array(f[-1]['boat'])-f[-1]['observation'])<=4.1
    assert np.linalg.norm(np.array(f[-2]['boat'])-f[-2]['observation'])>4.1
    assert story['duration']==f[-1]['t']

def test_grid_advects_without_changing_lane_shape(story):
    f=story['frames'];a=np.array(f[5]['routes']);b=np.array(f[31]['routes']);delta=b-a
    assert np.linalg.norm(delta[0,0])>100
    assert np.allclose(delta,delta[0,0])
    assert max(p[0] for route in f[5]['routes'] for p in route)<=-65+1e-6
    assert not any(f[5]['scanning']) and all(f[31]['scanning'])

def test_drone_spread_then_collapse(story):
    def span(t):
        p=np.array(story['frames'][t]['drones']);return np.linalg.norm(p[:,None]-p[None,:],axis=2).max()
    assert span(31)>150
    assert span(story['duration'])<40

def test_slow_surface_search_then_fast_intercept(story):
    f=story['frames']
    for t in range(5,32):assert np.linalg.norm(np.array(f[t]['boat'])-f[t-1]['boat'])<=.751
    assert np.linalg.norm(np.array(f[32]['boat'])-f[31]['boat'])>10
    assert np.linalg.norm(np.array(f[31]['boat'])-f[31]['truth'])>200
    gaps=[np.linalg.norm(np.array(x['boat'])-x['observation']) for x in f[32:]]
    assert all(b<a for a,b in zip(gaps,gaps[1:]))

def test_truth_separates_rapidly_without_feeding_planner(story):
    f=story['frames'];assert np.linalg.norm(f[15]['truth'])>100
    assert f[20]['center']!=f[20]['truth']
    assert len(f[20]['particles'])>100

def test_estimate_grows_before_lock_then_contracts(story):
    f=story['frames'];assert f[31]['area90']>f[5]['area90']
    assert f[32]['area90']<f[31]['area90']/10

def test_both_assets_launch_together(story):
    f=story['frames'];assert f[4]['drones']==f[0]['drones'] and f[4]['boat']==f[0]['boat']
    assert f[5]['drones']!=f[4]['drones'] and f[5]['boat']!=f[4]['boat']


def test_optimizer_selects_best_evaluated_candidate(story):
    plan=story['planning']
    assert len(plan['candidates'])==36
    assert plan['selected']['score']==max(c['score'] for c in plan['candidates'])
    assert plan['selected']['score']>min(c['score'] for c in plan['candidates'])
    assert 0<=plan['selected']['final_detection_proxy']<=1

def test_simulation_is_standalone_and_loads_only_bundled_assets():
    from html.parser import HTMLParser
    root=Path(__file__).resolve().parents[1]/'simulation'
    class Assets(HTMLParser):
        def handle_starttag(self,tag,attrs):
            assert tag!='iframe'
            for key,value in attrs:
                if key in ('src','href'):
                    assert not value.startswith(('http:','https:','/'))
                    assert (root/value).exists()
    Assets().feed((root/'index.html').read_text())
    js=(root/'mission-3d.js').read_text()
    assert 'WebSocket' not in js and '/api/' not in js
    assert js.count('fetch(')==1 and "fetch('./mission-drift.json')" in js
    assert (root/'vendor/three.module.js').is_file()
