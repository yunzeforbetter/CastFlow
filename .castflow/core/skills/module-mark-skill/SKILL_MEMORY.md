### Rule 1: A mark changes ownership. It does not create a skill

Anchors: [pattern:action, pattern:target_id]
Related: Rule 2, Pitfall 1

Definition
A mark is attach, split, keep, or review. It does not generate a programmer skill, and it does not turn each child file into its own module.

Check list
- [ ] Multi-select rows are still modules, not a count of marks
- [ ] A package under review stays on the list. It is not deleted

### Rule 2: Split the mechanism out. Do not take the surfaces with it

Anchors: [pattern:framework_mechanism, pattern:consumer_ids]
Related: Rule 3, Pitfall 2

Definition
A framework mechanism is a contract, a host, a scheduler, or a pipeline. High fan-in only means many callers use it. Feature surfaces that call it stay on the feature. Do not merge a surface into the mechanism package because it called the host.

Check list
- [ ] The split target does not contain paths of the consumer features
- [ ] A feature module's paths do not contain the mechanism package's contract files

### Rule 3: Attach only when the match is single. Do not park a shared package on its biggest caller

Anchors: [pattern:sibling_feature_id, pattern:consumer_ids]
Related: Rule 2, Pitfall 3

Definition
Attach only when the leaf name already matches one feature, or when there is exactly one consumer. With two or more consumers, use keep, and set the role to shared method or independent system. Do not merge into the feature with the largest fan-in.

Check list
- [ ] Attach evidence shows one consumer, or a leaf name equal to the target feature
- [ ] A package named like common, shared, or util did not enter a product feature just because a leaf name matched

### Rule 4: Jev only scores

Anchors: [pattern:source, pattern:weights]
Related: Pitfall 4

Definition
Always compute the structural prior first. Jev answers closed questions only after the user agrees to a provider, and only to adjust weights. Question criteria must not name a language, an engine, or a directory. If Jev was not called, source must not be `jev`, and a probability must not be invented. A wide disagreement sets source to `review`.

Check list
- [ ] Question criteria name no product-stack proper noun
- [ ] No request is sent without agreement
- [ ] Try a few packages first, then expand to the whole repo

### Rule 5: What is remembered is an accepted action

Anchors: [pattern:module-marks.txt]
Related: Rule 1, Pitfall 1

Definition
Only an attach, split, or keep the user accepted is written to `.castflow-runtime/module-marks.txt`. The next scan applies those lines, then the prior, then considers Jev. Do not write a GRAPH, a knowledge graph, or raw probabilities.

Check list
- [ ] The rules file has no probabilities and no raw model text
- [ ] A mark the user did not accept is not on disk

### Pitfall 1: Treating a residue package as one module

Anchors: [pattern:parent_id, pattern:child_ids]
Related: Rule 1, Rule 2

Symptom
A parent holds both per-feature surfaces and mechanism code, and cold start still gives it one skill.

Guard
If a parent has both feature leaves and mechanism leaves, mark first, then cut. Do not send the parent id straight into the multi-select.

### Pitfall 2: Using host fan-in to absorb every surface

Anchors: [pattern:framework_mechanism, pattern:fan_in]
Related: Rule 2

Symptom
The mechanism package has high fan-in, so every surface becomes its child module.

Guard
Fan-in identifies a mechanism. It does not swallow consumers. Consumers keep their own modules.

### Pitfall 3: A same-named leaf attaches a shared directory

Anchors: [pattern:leaf_name, pattern:shared_method]
Related: Rule 3

Symptom
A leaf in a shared-control directory happens to match a feature or a generic package, and is attached into a product module.

Guard
When the shared-method weight is higher than the feature weight, use keep. If it is still unclear, use review.

### Pitfall 4: A score written without Jev

Anchors: [pattern:jev_called, pattern:probability]
Related: Rule 4

Symptom
A probability is filled in while the interface is unavailable, or a simulation is described as a real call.

Guard
If Jev was not called, weights come only from the prior, and source is `prior` or `rule`. A simulation must say it is not a Jev return value.
