#!/usr/bin/env python3
"""Bake a deterministic cinematic fixture using Osprey's existing leeway ensemble.

Synthetic observation/occlusion times are narrative inputs, not detector performance.
Search planning receives ONLY the estimate cloud, never the hidden casualty trajectory.
"""
from __future__ import annotations

import json
import copy
from pathlib import Path

import numpy as np

from osprey.drift import Forcing, LeewayEnsemble, polygon_area
from osprey.geo import LatLon

ROOT = Path(__file__).resolve().parents[2]
SCALE = 60.0  # drift model seconds per storyboard second, independent of UI playback rate
LAUNCH, LOCK, END = 5, 32, 120


def search_routes(cloud: np.ndarray, count: int = 5) -> list[list[list[float]]]:
    """Equal-width parallel sweeps aligned with the ensemble's principal axes.

    A transparent probability-oriented heuristic, not an optimized SAR search planner.
    Routes adapt to posterior location, orientation and spread. No truth input.
    """
    center = np.median(cloud, axis=0)
    values, vectors = np.linalg.eigh(np.cov(cloud.T))
    along = vectors[:, -1]
    if along[0] < 0:
        along = -along
    across = np.array([-along[1], along[0]])
    projected = (cloud - center) @ np.stack([along, across], axis=1)
    length, width = np.maximum(np.percentile(abs(projected), 90, axis=0), [85.0, 110.0])
    routes = []
    for i in range(count):
        points = []
        for j in range(2):
            lane = -width + 2 * width * (i + (j + .5) / 2) / count
            for end in (-1, 1) if j % 2 == 0 else (1, -1):
                points.append((center + end * length * along + lane * across).tolist())
        routes.append(points)
    # Keep the illustrative aerial search offshore, clear of the launch vessel.
    # Translation uses only the planned grid extent, never hidden truth.
    maximum_east = max(p[0] for route in routes for p in route)
    offset = max(0, maximum_east + 65)
    return [[[x-offset, y] for x,y in route] for route in routes]


def step_toward(position, goal, distance):
    delta = np.asarray(goal) - position
    return position + delta * min(1.0, distance / max(float(np.linalg.norm(delta)), 1e-9))


def drift_grid(cloud, direction, spacing, angle=0., offset=0., count=5):
    """Disjoint parallel lanes in a translating target-drift reference frame."""
    along=np.array(direction,dtype=float);along/=max(np.linalg.norm(along),1e-9)
    c,s=np.cos(angle),np.sin(angle);along=np.array([[c,-s],[s,c]])@along
    across=np.array([-along[1],along[0]])
    center=np.median(cloud,axis=0)+along*offset
    half_length=max(65.,float(np.percentile(abs((cloud-center)@along),85)))
    routes=[]
    for i in range(count):
        points=[]
        for j in range(2):
            lane=(i*2+j-(count*2-1)/2)*spacing
            for end in (-1,1) if j%2==0 else (1,-1):
                points.append(center+along*half_length*end+across*lane)
        routes.append(points)
    routes=np.array(routes)
    routes[:,:,0]-=max(0,float(routes[:,:,0].max())+65)
    return routes


def simulate_search(base_routes, shifts, initial):
    positions=np.array(initial,dtype=float).copy();indexes=[0]*5;active=[False]*5
    history=[]
    for shift in shifts:
        routes=base_routes+shift
        before=positions.copy()
        for i in range(5):
            goal=routes[i,indexes[i]%4]
            if np.linalg.norm(goal-positions[i])<18:
                active[i]=True;indexes[i]+=1;goal=routes[i,indexes[i]%4]
            positions[i]=step_toward(positions[i],goal,18.)
        history.append((before,positions.copy(),active.copy()))
    return history


def score_search(history, clouds):
    """Toy detection law on relative swept segments; reward earlier cumulative detection.

    Cross-track sigma=12m, peak per-step detection=0.65 are assumptions, not sensor data.
    Repeated exposures are treated as conditionally independent for candidate comparison.
    """
    miss=np.ones(len(clouds[0]));scores=[]
    previous=clouds[0]
    for (before,after,active),cloud in zip(history,clouds):
        no_detection=np.ones(len(cloud))
        for i in range(5):
            if not active[i]:continue
            a=previous-before[i];b=cloud-after[i];v=b-a
            fraction=np.clip(-np.sum(a*v,axis=1)/np.maximum(np.sum(v*v,axis=1),1e-9),0,1)
            distance=np.linalg.norm(a+fraction[:,None]*v,axis=1)
            pd=.65*np.exp(-.5*(distance/12.)**2)
            no_detection*=1-pd
        miss*=no_detection;scores.append(float(1-miss.mean()));previous=cloud
    return float(np.mean(scores)),float(1-miss.mean())


def optimize_search(estimate, initial):
    """Exhaustive choice within 36 candidate grids, not global SAR optimization."""
    future=copy.deepcopy(estimate);clouds=[]
    for k in range(LOCK-LAUNCH):
        if k:future.advance_to(estimate.t+k*SCALE,dt=3)
        clouds.append(future.xy.copy())
    centers=np.array([np.median(c,axis=0) for c in clouds])
    shifts=centers-centers[0]
    direction=centers[-1]-centers[0]
    candidates=[];best=None
    for angle in (0.,-np.pi/6,np.pi/6,np.pi/2):
        for spacing in (20.,30.,40.):
            for offset in (-40.,0.,40.):
                routes=drift_grid(clouds[6],direction,spacing,angle,offset)
                history=simulate_search(routes,shifts,initial)
                score,final=score_search(history,clouds)
                info=dict(angle_deg=float(np.degrees(angle)),spacing_m=spacing,offset_m=offset,
                          score=score,final_detection_proxy=final)
                candidates.append(info)
                if best is None or score>best[0]:best=(score,routes,info)
    return best[1],shifts,dict(selected=best[2],candidates=candidates,
        objective='Mean cumulative detection proxy over the 27-story-second search horizon',
        sensor_assumptions='12 m cross-track sigma; peak detection 0.65 per step; independent repeated looks',
        scope='Best of 36 constrained drift-relative grids; not a validated globally optimal SAR plan')


def build():
    forcing = Forcing.load()
    origin = LatLon(42.35, -70.8)
    truth = LeewayEnsemble(origin, forcing, n=1, obj='PIW-2',
                          rng=np.random.default_rng(741), seed_sigma_m=0, diffusivity=.05)
    rng = np.random.default_rng(2901)
    estimate = LeewayEnsemble(origin, forcing, n=800, rng=np.random.default_rng(37), seed_sigma_m=14)
    last_observation = np.array([0., 0.])
    seed_story = 3
    positions = np.array([[-62,-18],[-52,-18],[-62,-8],[-52,-8],[-42,-18]], dtype=float)
    boat = np.array([-77., -13.])
    indexes = [0] * 5
    boat_index = 0
    scanning = [False] * 5
    frames = []
    routes = search_routes(estimate.xy)
    surface_route = search_routes(estimate.xy, 1)[0]
    base_routes=None;shifts=None;planning=None
    for t in range(END + 1):
        elapsed = max(0, min(t, LOCK)-3) * SCALE + max(0, t-LOCK)*6
        truth.advance_to(elapsed, dt=3)
        observed = t >= LOCK
        if observed:
            # An explicit synthetic measurement, independent of ensemble random draws.
            last_observation = truth.xy[0] + rng.normal(0, .7, 2)
            estimate = LeewayEnsemble(origin, forcing, n=800,
                                     rng=np.random.default_rng(rng.integers(1 << 31)), seed_sigma_m=2)
            estimate.xy += last_observation
            seed_story = t
        else:
            estimate.advance_to(max(0, t-seed_story)*SCALE, dt=3)
        if t == LAUNCH:
            base_routes,shifts,planning=optimize_search(estimate,positions)
            # Surface asset preserves the requested near-launch slow search allocation.
            _,_,cu,cv=forcing.at(0);along=np.array([cu,cv]);along/=np.linalg.norm(along)
            across=np.array([-along[1],along[0]]);anchor=np.array([-65.,-4.])
            surface_route=[(anchor+along*x+across*y).tolist() for x,y in [(-15,-12),(15,-12),(15,12),(-15,12)]]
            indexes=[0]*5;boat_index=0
        if base_routes is not None:
            shift=shifts[min(t-LAUNCH,len(shifts)-1)]
            routes=(base_routes+shift).tolist()
        center = np.median(estimate.xy, axis=0)
        if t >= LAUNCH:
            for i in range(5):
                if observed:
                    angle = 2*np.pi*i/5
                    goal = last_observation + np.array([np.cos(angle),np.sin(angle)])*16
                else:
                    goal = routes[i][indexes[i] % len(routes[i])]
                    if np.linalg.norm(np.asarray(goal)-positions[i]) < 18:
                        scanning[i] = True
                        indexes[i] += 1
                        goal = routes[i][indexes[i] % len(routes[i])]
                positions[i] = step_toward(positions[i], goal, 18.0)
            if observed:
                # Direct intercept from the current USV position to the latest observation.
                delta = boat-last_observation
                goal = last_observation + delta/max(np.linalg.norm(delta),1e-9)*4
            else:
                goal = surface_route[boat_index % len(surface_route)]
                if np.linalg.norm(np.asarray(goal)-boat) < 4:
                    boat_index += 1
                    goal = surface_route[boat_index % len(surface_route)]
            boat = step_toward(boat, goal, 16.0 if observed else .75)  # slower than every aircraft
        f = dict(t=t, model_s=elapsed, since_fix_s=max(0,t-seed_story)*SCALE,
                 observed=observed, rough=False, scanning=scanning.copy(),
                 truth=truth.xy[0].tolist(), observation=last_observation.tolist(),
                 center=center.tolist(), particles=estimate.xy[::6].tolist(),
                 hull50=estimate.hull(.5).tolist(), hull90=estimate.hull(.9).tolist(),
                 area90=polygon_area(estimate.hull(.9)), routes=routes,
                 surface_route=surface_route, drones=positions.tolist(), boat=boat.tolist())
        frames.append(f)
        if observed and np.linalg.norm(boat-last_observation) <= 4.1:
            break
    wu,wv,cu,cv = forcing.at(0)
    return dict(version=6, planning=planning, duration=frames[-1]["t"], model_scale=SCALE, tracking_model_scale=6, particles=800,
                model='Osprey LeewayEnsemble · PIW-1 estimate / PIW-2 hidden scenario',
                forcing=forcing.label, forcing_source=forcing.source,
                forcing_time=forcing.t0_iso, forcing_license='Open-Meteo CC BY 4.0 (archived repository snapshot)', wind_enu=[wu,wv], current_enu=[cu,cv],
                coordinates='local ENU meters, seeded at water entry',
                acquisition='Scripted positive lock at 32 s, then continuous sightings until USV rendezvous; not a detector test',
                planner='Best of 36 drift-following parallel grids under an assumed detection model; current-aligned local USV search',
                probabilities='Central 50% and 90% of the simulated ensemble; not calibrated real-world coverage',
                frames=frames)


if __name__ == '__main__':
    output=ROOT/'simulation/mission-drift.json'
    data=build()
    # Compact coordinates for browser delivery without changing generated planning decisions.
    def rounded(x):
        if isinstance(x, float): return round(x,3)
        if isinstance(x, list): return [rounded(v) for v in x]
        if isinstance(x, dict): return {k:rounded(v) for k,v in x.items()}
        return x
    output.write_text(json.dumps(rounded(data),separators=(',',':')))
    print(f'Generated {len(data["frames"])} frames at {output}')
