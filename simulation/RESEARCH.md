# Research basis for the demo search planner

Research checked November 7, 2026. The implementation is a constrained simulation comparison, not operational SAR guidance.

## Sources and conclusions

1. [US Coast Guard Addendum, COMDTINST 16130.2H, §3.3](https://www.dco.uscg.mil/Portals/9/CG-5R/MassRescueOps/CGADD%20COMDINST%2016130_2H.pdf?ver=tYaRnfVEGQhBxk3HXkimww%3D%3D). Search planning combines a target-location distribution, detection capability and finite search effort. The aim is high probability of success quickly. This supports evaluating candidate plans against particles and an explicit sensor assumption rather than labeling a visually appealing grid “optimal.” The indexed official document text was available; direct PDF retrieval returned HTTP 403.

2. [USCG Addendum, search-pattern discussion](https://media.defense.gov/2025/Jul/17/2003756425/-1/-1/0/CI_16130_2H.PDF). Track spacing affects coverage through effective sweep width. Its sector-search discussion describes a search area moving with a floating datum. Our broader, multi-aircraft demonstration uses translating parallel lanes; this is an engineering adaptation, not a claim that the manual prescribes this exact formation. The indexed official text was available; direct PDF retrieval returned HTTP 403.

3. [Marques, Escribano Macias and Angeloudis, Probabilistic Planning for Maritime Search and Rescue (2023)](https://arxiv.org/html/2306.03871v1). The paper formalizes time-sensitive probabilistic planning and discusses how sensor performance and coverage interact. It supports penalizing late discovery and explicitly modeling detection. Its thermal-camera parameters are not transferred to the Aquila16 prototype.

## Implementation decision

Use five disjoint two-lane sweeps in a moving drift reference frame. Keep orientation and spacing fixed during the search leg; translate the grid smoothly using the ensemble forecast. Aligning with flow is a candidate, not an axiom: cross-flow lanes can score better depending on the predicted distribution and access time. A finite search compares 36 layouts with the same drift trajectories, vehicle speed and search horizon. The selected plan is the best evaluated candidate under assumed detection, not proof of global optimality.

The current deterministic run chooses +30° relative to net target drift, 20 m lane spacing and zero longitudinal offset. The toy model's detection proxy is deliberately not presented as an operational success percentage. The model accounts for water current plus wind-driven leeway; water flow and a floating person's net drift are distinct. A blue water-current arrow makes that distinction visible.

To move beyond a demo, measure sensor detection versus range/altitude/sea state, use real vehicle endurance and turn limits, validate environmental forecasts, and compare additional path families and uncertainty assumptions. None of those missing measurements can be replaced by selecting a named pattern from a manual.
