## Example 1: An evidence card, not a directory rule

Scene
Cold start has already named the candidate package. A mark consumes only this card. The card may name a path from this repo. The question text must not name a directory from one technology stack.

Code
```
id: presentation-residue
parent_id: presentation
leaf_name: orders-view
sibling_feature_id: orders
fan_in: 2
fan_out: 4
entry_count: 6
consumer_ids: [orders]
decl_sample: [OrderView, OrderRow]
child_ids: []
```

Project reference
`.castflow/core/skills/module-mark-skill/marks.schema.json` fields `sibling_feature_id`, `consumer_ids`

## Example 2: Ask all four stances at once

Scene
The structural prior cannot tell a surface contract from one feature's surface. Hand the same card to Jev. The four questions do not read each other's answers. Without a provider the user agreed to, do not send a request, and do not invent a probability.

Code
```
{
  "state": "id=interaction-kernel fan_in=40 fan_out=3 entry_count=0 consumer_ids=orders,billing,search decl_sample=ViewHost,OpenView",
  "questions": {
    "stance": {
      "type": "choice",
      "instructions": "Which engineering stance best fits this package?",
      "criteria": {
        "feature": "One product ability with its own entries",
        "shared_method": "Generic helper used by many abilities, no product entry",
        "independent_system": "A whole subsystem with its own surface, not a helper",
        "framework_mechanism": "Contracts, hosts, or schedulers that many surfaces sit on"
      }
    },
    "framework_mechanism": {
      "type": "score",
      "instructions": "Strength of framework-mechanism evidence. Use the rubric index.",
      "criteria": {
        "0": "No shared contract or host",
        "1": "Weak",
        "2": "Mixed",
        "3": "Mostly a mechanism",
        "4": "Only a mechanism; surfaces live elsewhere"
      }
    }
  }
}
```

Project reference
`.castflow/core/skills/module-mark-skill/SKILL.md` duty 2

## Example 3: Attach a same-named leaf to an existing feature

Scene
The parent is a large residue. The child leaf name matches the existing feature `orders`, and the only consumer is `orders`. The action is attach. Do not merge the child into the mechanism package because the child calls `ViewHost`.

Code
```
id: orders-view
action: attach
target_id: orders
role: feature
weights: {feature: 0.8, shared_method: 0.1, independent_system: 0.0, framework_mechanism: 0.1}
source: prior
evidence: leaf matches feature orders; only consumer is orders
```

Project reference
`.castflow/core/skills/module-mark-skill/marks.schema.json` field `action`

## Example 4: Split the mechanism out; leave callers where they are

Scene
Declarations in `interaction-kernel` are a host and contracts. Fan-in comes from many features. The package has no product entry of its own. The action is split. Feature packages stay as they are.

Code
```
id: interaction-kernel
action: split
target_id: interaction-kernel
role: engine
weights: {feature: 0.0, shared_method: 0.2, independent_system: 0.1, framework_mechanism: 0.9}
source: prior
evidence: fan-in 40 from feature packages; entry_count 0; names are host and contract
```

Project reference
`.castflow/core/skills/module-mark-skill/SKILL_MEMORY.md` Rule 2

## Example 5: Remember only after acceptance

Scene
The user accepts the split and the attach. Write only the accepted actions as rules. Do not write probabilities. Do not write a graph.

Code
```
attach <orders-view path prefix> orders
split <interaction-kernel path prefix> interaction-kernel engine
keep <shared-rows path prefix> shared-rows tool
```

Project reference
`.castflow/core/skills/module-mark-skill/SKILL.md` duty 4
