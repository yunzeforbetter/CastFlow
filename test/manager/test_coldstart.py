#!/usr/bin/env python3
"""Cold-start: package atoms, one dependency tree, role labels, one skill."""

from __future__ import print_function

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_CASTFLOW = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".castflow"
))
sys.path.insert(0, _CASTFLOW)

from manager import coldstart


FIXTURE = {
    "Assets/Scripts/Battle/BattleRunner.cs": (
        "public class BattleRunner {\n"
        "    public void Start() { var h = new BattleHelper(); }\n"
        "}\n"
    ),
    "Assets/Scripts/Battle/BattleHelper.cs": (
        "public class BattleHelper { public void Tick() {} }\n"
    ),
    "Assets/Scripts/Battle/BattleStart.cs": (
        "public class BattleStart {\n"
        "    void Run() { var a = new BattleRunner(); var b = new BattleRunner(); }\n"
        "    void More() { BattleRunner ready = null; }\n"
        "}\n"
    ),
    "Assets/Scripts/Util/MathUtil.cs": (
        "public static class MathUtil {\n"
        "    public static int Add(int a, int b) { return a + b; }\n"
        "}\n"
    ),
    "Assets/Scripts/UI/Hud.cs": (
        "using Game.Battle;\n"
        "public class Hud {\n"
        "    void Show() { var x = new BattleRunner(); }\n"
        "    void Again() { var y = new BattleRunner(); }\n"
        "    void Hold() { BattleRunner runner = null; MathUtil.Add(1, 2); }\n"
        "}\n"
    ),
    "Assets/Scripts/Town/TownHall.cs": (
        "public class TownHall {\n"
        "    void Open() { var x = new BattleRunner(); MathUtil.Add(2, 3); }\n"
        "}\n"
    ),
    "Assets/Scripts/Mail/MailBox.cs": (
        "public class MailBox { }\n"
    ),
    "Assets/Scripts/Town/TownCrier.cs": (
        "public class TownCrier { void Ding() { var m = new MailBox(); } }\n"
    ),
    "Assets/Scripts/Tests/BattleTests.cs": (
        "public class BattleTests { }\n"
    ),
    "Assets/Scripts/Editor/BattleEditor.cs": (
        "public class BattleEditor { }\n"
    ),
    "Assets/Scripts/OnlyUsing/OnlyUsing.cs": (
        "using BattleRunner;\n"
        "public class OnlyUsing { }\n"
    ),
    "Assets/Scripts/Quest/QuestLog.cs": (
        "public class QuestLog { }\n"
    ),
    "Library/Secret.cs": (
        "public class SecretType { public void Boom() { var x = new BattleRunner(); } }\n"
    ),
    "Packages/Vendor.cs": (
        "public class VendorType { }\n"
    ),
    "Assets/Prefabs/Hero.prefab": "not a script",
}


def _by_id(cards):
    return {card["id"]: card for card in cards}


class ColdStartTests(unittest.TestCase):
    def cards(self, target=None, role_rules=None):
        return coldstart.analyze_sources(
            FIXTURE, target=target, role_rules=role_rules,
        )

    def test_using_is_not_an_edge_and_weight_is_not_token_count(self):
        cards = _by_id(self.cards())
        battle = cards["battle"]
        # Hud 3 + TownHall 1. BattleStart is inside the battle atom, so those
        # three tokens are not a package edge. OnlyUsing and Library add nothing.
        self.assertEqual(battle["symbol_fanin"].get("BattleRunner"), 4)
        self.assertEqual(battle["frequency"], 2)
        self.assertNotIn("secret-type", cards)
        self.assertNotIn("vendor-type", cards)
        self.assertNotIn("MathUtil", battle["core_symbols"])
        self.assertTrue(all("Util/" not in path for path in battle["paths"]))
        self.assertIn("BattleHelper", battle["core_symbols"])
        self.assertTrue(any(path.endswith("BattleHelper.cs") for path in battle["paths"]))
        self.assertNotIn("skill cluster", battle["responsibility"].lower())

    def test_packages_are_not_path_prefixes_or_one_type_modules(self):
        cards = self.cards()
        by_id = _by_id(cards)
        self.assertIn("battle", by_id)
        self.assertNotIn("game-logic-logic", by_id)
        self.assertNotIn("battle-runner", by_id)
        battle = by_id["battle"]
        self.assertEqual(battle["role"], "engine")
        self.assertEqual(battle["recommend"], "yes")
        self.assertEqual([item["id"] for item in battle["atoms"]], ["battle"])
        self.assertGreaterEqual(len(battle["core_symbols"]), 3)
        for symbol in battle["core_symbols"]:
            self.assertNotIn("/", symbol)
            self.assertFalse(symbol.endswith(".cs"))
        for required in ("util", "tests", "editor"):
            self.assertIn(required, by_id)
            self.assertEqual(by_id[required]["recommend"], "no")
        self.assertEqual(by_id["util"]["role"], "tool")
        self.assertIn(by_id["ui"]["role"], ("feature",))
        self.assertEqual(by_id["ui"]["recommend"], "yes")
        self.assertGreater(by_id["ui"]["entries"], 0)

    def test_same_feature_under_logic_and_runtime_is_one_atom(self):
        sources = {
            "Assets/Scripts/GameLogic/Logic/Modules/Mail/MailBox.cs": (
                "public class MailBox { public void Open() { MailWindow w = null; } }\n"
            ),
            "Assets/Scripts/GameLogic/Runtime/Game/Modules/Mail/MailWindow.cs": (
                "public class MailWindow {\n"
                "    void Show() { var a = new MailBox(); var b = new MailBox(); var c = new MailBox(); }\n"
                "}\n"
            ),
            "Assets/Scripts/GameLogic/Logic/Modules/Mission/MissionList.cs": (
                "public class MissionList { void Go() { MissionWindow w = null; } }\n"
            ),
            "Assets/Scripts/GameLogic/Runtime/Game/Modules/Mission/MissionWindow.cs": (
                "public class MissionWindow { void Show() { var m = new MissionList(); } }\n"
            ),
            "Assets/Scripts/GameLogic/Logic/Loose.cs": (
                "public class GameManager { void Boot() { var m = new MailBox(); } }\n"
            ),
        }
        cards = _by_id(coldstart.analyze_sources(sources))
        self.assertIn("mail", cards)
        self.assertIn("mission", cards)
        self.assertNotIn("game-logic-logic", cards)
        self.assertNotIn("game-logic-runtime", cards)
        mail_paths = " ".join(cards["mail"]["paths"])
        self.assertIn("Logic/Modules/Mail/MailBox.cs", mail_paths)
        self.assertIn("Runtime/Game/Modules/Mail/MailWindow.cs", mail_paths)
        self.assertNotIn("Mission", cards["mail"]["core_symbols"])
        self.assertEqual(cards["mail"]["role"], "feature")
        self.assertEqual(cards["mail"]["recommend"], "yes")

    def test_protocol_is_an_adapter_and_repeated_tokens_count_once(self):
        body = "public class MailWindow {\n"
        for _ in range(30):
            body += "    void Use() { TType t = TType.Stop; }\n"
        body += "}\n"
        sources = {
            "tools/Tuyoo.Protocol/TType.cs": "public enum TType { Stop }\n",
            "Assets/Scripts/Tools/AmplifyShaderEditor/ShaderNode.cs": (
                "public class ShaderNode { }\n"
            ),
            "Assets/Scripts/GameLogic/Logic/Modules/Mail/MailBox.cs": body,
        }
        cards = _by_id(coldstart.analyze_sources(sources))
        self.assertEqual(cards["protocol"]["role"], "adapter")
        self.assertEqual(cards["protocol"]["recommend"], "no")
        self.assertEqual(cards["protocol"]["frequency"], 1)
        # Each line names TType twice. Package frequency stays 1 distinct type.
        self.assertEqual(cards["protocol"]["symbol_fanin"].get("TType"), 60)
        self.assertEqual(cards["amplify-shader-editor"]["role"], "adapter")
        self.assertEqual(cards["amplify-shader-editor"]["recommend"], "no")
        self.assertNotIn("TType", cards["mail"]["core_symbols"])
        self.assertNotIn("skill cluster", cards["protocol"]["responsibility"].lower())

    def test_role_rule_overrides_before_the_cut(self):
        cards = _by_id(self.cards(role_rules=[("battle", "tool")]))
        self.assertEqual(cards["battle"]["role"], "tool")
        self.assertEqual(cards["battle"]["recommend"], "no")

    def test_coarser_target_is_a_union_of_the_finer_cut(self):
        sources = {}
        for index in range(36):
            name = "Feat{:02d}".format(index)
            prev = "Feat{:02d}".format(max(index - 1, 0))
            sources[
                "Assets/Scripts/GameLogic/Logic/Modules/{0}/{0}Window.cs".format(name)
            ] = (
                "public class {0}Window {{\n"
                "    void Show() {{ var a = new {1}Window(); var b = new Feat00Window(); }}\n"
                "}}\n"
            ).format(name, prev)
        fine = coldstart.analyze_sources(sources, target=30)
        coarse = coldstart.analyze_sources(sources, target=8)
        self.assertGreater(len(fine), len(coarse))
        self.assertLessEqual(len(coarse), 8)
        self.assertGreaterEqual(len(fine), 30)
        self.assertTrue(coldstart.cut_contains(coarse, fine))
        fine_atoms = sorted(atom["id"] for card in fine for atom in card["atoms"])
        coarse_atoms = sorted(atom["id"] for card in coarse for atom in card["atoms"])
        self.assertEqual(fine_atoms, coarse_atoms)
        self.assertIn("feat00", fine_atoms)
        self.assertIn("feat35", fine_atoms)

    def test_two_analyses_match(self):
        first = coldstart.format_summary(self.cards())
        second = coldstart.format_summary(coldstart.analyze_sources(dict(FIXTURE)))
        self.assertEqual(first, second)
        self.assertIn("\natoms: ", first)
        self.assertIn("\ntarget: ", first)
        self.assertNotIn("skill cluster", first)

    def test_focus_dirs_keep_roots_not_every_leaf(self):
        leaves = [
            "Assets/Scripts/Game/Modules/NewCity/A",
            "Assets/Scripts/Game/Modules/NewCity/B",
            "Assets/Scripts/Game/Modules/NewCity/C/D",
            "Assets/Scripts/Game/Runtime/NewCity/E",
            "Assets/Scripts/Game/Runtime/NewCity/F",
        ]
        self.assertEqual(
            coldstart.focus_script_dirs(leaves, limit=6),
            [
                "Assets/Scripts/Game/Modules/NewCity/A",
                "Assets/Scripts/Game/Modules/NewCity/B",
                "Assets/Scripts/Game/Modules/NewCity/C/D",
                "Assets/Scripts/Game/Runtime/NewCity/E",
                "Assets/Scripts/Game/Runtime/NewCity/F",
            ],
        )
        self.assertEqual(
            coldstart.focus_script_dirs(leaves, limit=2),
            [
                "Assets/Scripts/Game/Modules/NewCity",
                "Assets/Scripts/Game/Runtime/NewCity",
            ],
        )

    def test_selection_writes_only_chosen_card(self):
        root = tempfile.mkdtemp(prefix="castflow-cold-")
        self.addCleanup(shutil.rmtree, root, True)
        cards = self.cards()
        chosen = coldstart.select_cards(cards, ["battle"])
        written = coldstart.write_selected_queue(root, chosen)
        self.assertEqual(len(written), 1)
        names = os.listdir(coldstart.queue_dir(root))
        self.assertEqual(names, ["01-battle.yaml"])
        text = open(written[0], "r", encoding="utf-8").read()
        self.assertIn("status: pending", text)
        self.assertIn("language: en", text)
        self.assertIn("id: battle", text)
        self.assertIn("role: engine", text)
        self.assertIn("responsibility:", text)
        self.assertIn("Assets/Scripts/Battle", text)
        self.assertNotIn("core_symbols:", text)
        self.assertNotIn("scope_paths:", text)
        self.assertNotIn("BattleHelper.cs", text)
        self.assertNotIn("MathUtil", text)
        self.assertNotIn("skill cluster", text)
        for forbidden in coldstart.LEDGER_NAMES:
            self.assertFalse(os.path.exists(os.path.join(root, forbidden)))
        self.assertFalse(os.path.isdir(os.path.join(root, ".ua")))

    def test_queue_card_language_follows_cold_start(self):
        from manager import config
        root = tempfile.mkdtemp(prefix="castflow-lang-")
        self.addCleanup(shutil.rmtree, root, True)
        config.save_config(root, {"language": "zh"})
        chosen = coldstart.select_cards(self.cards(), ["battle"])
        written = coldstart.write_selected_queue(root, chosen)
        text = open(written[0], "r", encoding="utf-8").read()
        self.assertIn("language: zh", text)
        self.assertNotIn("language: en", text)

    def test_skill_uses_real_call_sites_inside_the_node(self):
        root = tempfile.mkdtemp(prefix="castflow-skill-")
        self.addCleanup(shutil.rmtree, root, True)
        battle = _by_id(self.cards())["battle"]
        hits = coldstart.collect_call_sites(FIXTURE, battle, limit=8)
        self.assertGreaterEqual(len(hits), 3)
        self.assertLessEqual(len(hits), 8)
        allowed = set(battle["paths"])
        for hit in hits:
            self.assertNotIn("class BattleRunner", hit["text"])
            self.assertFalse(hit["text"].startswith("using "))
            self.assertIn(hit["path"], allowed)
            self.assertNotIn("MathUtil", hit["text"])
            self.assertNotIn("Hud.cs", hit["path"])
        folder, used = coldstart.write_programmer_skill(root, battle, FIXTURE, hits)
        self.assertTrue(folder.endswith("programmer-battle-skill"))
        self.assertEqual(
            set(os.listdir(folder)), {"SKILL.md", "EXAMPLES.md"})
        examples = open(os.path.join(folder, "EXAMPLES.md"), "r", encoding="utf-8").read()
        skill = open(os.path.join(folder, "SKILL.md"), "r", encoding="utf-8").read()
        self.assertGreaterEqual(examples.count("## Example "), 3)
        self.assertLessEqual(examples.count("## Example "), 8)
        for hit in used:
            self.assertIn(hit["text"], examples)
        self.assertNotIn("## 示例", examples)
        self.assertIn("Change battle in this repo.", skill)
        self.assertNotIn("Change battle (battle)", skill)
        description = skill.split("description: ", 1)[1].split("\n", 1)[0]
        self.assertEqual(description.count("NOT"), 1)
        self.assertIn("battle", description)
        self.assertNotIn("SKILL_MEMORY.md", skill)
        self.assertNotIn("ITERATION_GUIDE.md", skill)
        self.assertNotIn("skill cluster", skill.lower())
        self.assertNotIn("Hud.cs", examples)
        problems = coldstart.heat_path_violations(battle, used, examples + skill)
        self.assertEqual(problems, [])
        print("cold-start call-site text kept: {}".format(
            all(hit["text"] in examples for hit in used)))
        print("cold-start single module-id NOT: {}".format(
            "NOT" in skill and "battle" in skill and "(battle)" not in skill))

    def test_cold_start_without_call_sites_does_not_invent_examples(self):
        root = tempfile.mkdtemp(prefix="castflow-empty-skill-")
        self.addCleanup(shutil.rmtree, root, True)
        card = {
            "id": "quiet",
            "name": "Quiet",
            "suggested_skill": "programmer-quiet-skill",
        }
        folder, used = coldstart.write_programmer_skill(
            root, card, {}, call_sites=[])
        self.assertEqual(used, [])
        self.assertEqual(set(os.listdir(folder)), {"SKILL.md"})
        skill = open(os.path.join(folder, "SKILL.md"), "r", encoding="utf-8").read()
        description = skill.split("description: ", 1)[1].split("\n", 1)[0]
        self.assertIn("quiet", description)
        self.assertEqual(description.count("NOT"), 1)
        self.assertNotIn("Change quiet (quiet)", skill)
        self.assertIn("Do not invent an entry.", skill)
        self.assertNotIn("## Example", skill)

    def test_cli_entry_on_temp_tree(self):
        root = tempfile.mkdtemp(prefix="castflow-cli-")
        self.addCleanup(shutil.rmtree, root, True)
        for rel, text in FIXTURE.items():
            if rel.startswith("Library/") or rel.startswith("Packages/"):
                continue
            if not rel.endswith(".cs"):
                continue
            full = os.path.join(root, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        secret = os.path.join(root, "Library", "Secret.cs")
        os.makedirs(os.path.dirname(secret), exist_ok=True)
        with open(secret, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(FIXTURE["Library/Secret.cs"])
        rules = os.path.join(root, ".castflow-runtime", "module-roles.txt")
        os.makedirs(os.path.dirname(rules), exist_ok=True)
        with open(rules, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("# project override\nutil tool\n")
        loaded = coldstart.load_role_rules(root)
        self.assertEqual(loaded, [("util", "tool")])
        manager = os.path.join(_CASTFLOW, "manager.py")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        first = subprocess.check_output(
            [sys.executable, manager, "coldstart", "--root", root],
            env=env, text=True,
        )
        second = subprocess.check_output(
            [sys.executable, manager, "coldstart", "--root", root],
            env=env, text=True,
        )
        self.assertEqual(first, second)
        self.assertIn("\nbattle\t", "\n" + first)
        self.assertIn("atoms:", first)
        self.assertNotIn("secret-type", first)
        self.assertNotIn("skill cluster", first)
        modules = int(first.split("modules: ", 1)[1].splitlines()[0])
        atoms = int(first.split("atoms: ", 1)[1].splitlines()[0])
        self.assertGreaterEqual(atoms, modules)
        self.assertFalse(os.path.isdir(coldstart.queue_dir(root)))
        queued = subprocess.check_output(
            [sys.executable, manager, "coldstart", "--root", root,
             "--select", "battle", "--queue"],
            env=env, text=True,
        )
        self.assertIn("queue-file: 01-battle.yaml", queued)
        names = os.listdir(coldstart.queue_dir(root))
        self.assertEqual(names, ["01-battle.yaml"])
        skilled = subprocess.check_output(
            [sys.executable, manager, "coldstart", "--root", root,
             "--select", "battle", "--skill"],
            env=env, text=True,
        )
        self.assertIn("examples: ", skilled)
        self.assertIn("queue-removed: yes", skilled)
        self.assertFalse(os.path.exists(coldstart.queue_dir(root)))
        self.assertTrue(os.path.isdir(coldstart.skill_dir(root, "battle")))
        for forbidden in coldstart.LEDGER_NAMES:
            self.assertFalse(os.path.exists(os.path.join(root, forbidden)))


class SkillGateTests(unittest.TestCase):
    def test_description_uses_module_id_and_one_sibling(self):
        cards = [
            {"id": "city", "role": "feature", "atoms": [{"id": "city"}], "kind": "feature-dir", "frequency": 3, "entries": 0, "file_count": 10, "suggested_skill": "programmer-city-skill", "name": "KeyValuePair"},
            {"id": "new-city", "role": "feature", "atoms": [{"id": "new-city"}], "kind": "feature-dir", "frequency": 9, "entries": 4, "file_count": 20, "suggested_skill": "programmer-new-city-skill", "name": "Object"},
            {"id": "battle", "role": "feature", "atoms": [{"id": "battle"}], "kind": "feature-dir", "frequency": 4, "entries": 1, "file_count": 8, "suggested_skill": "programmer-battle-skill"},
            {"id": "battle-logic", "role": "engine", "atoms": [{"id": "battle-logic"}], "kind": "asmdef", "frequency": 6, "entries": 0, "file_count": 12, "suggested_skill": "programmer-battle-logic-skill"},
            {"id": "protocol", "role": "adapter", "atoms": [{"id": "protocol"}], "kind": "adapter-path", "frequency": 40, "entries": 0, "file_count": 100, "suggested_skill": "programmer-protocol-skill"},
            {"id": "grab", "role": "engine", "atoms": [{"id": "grab"}, {"id": "other"}], "kind": "asmdef", "frequency": 10, "entries": 0, "file_count": 50, "suggested_skill": "programmer-grab-skill"},
        ]
        coldstart._apply_recommend(cards)
        by_id = {card["id"]: card for card in cards}
        city = coldstart.programmer_description(by_id["city"])
        new_city = coldstart.programmer_description(by_id["new-city"])
        battle = coldstart.programmer_description(by_id["battle"])
        self.assertIn("Use when the user names city.", city)
        self.assertIn("NOT new-city.", city)
        self.assertNotIn("KeyValuePair", city)
        self.assertNotIn("Object", new_city)
        self.assertNotIn("NOT other programmer", city)
        self.assertNotIn("NOT other programmer", new_city)
        self.assertEqual(city.count("NOT"), 1)
        self.assertIn("NOT battle-logic.", battle)
        self.assertNotIn("(city)", city)
        self.assertNotIn("a different module", city)
        solo = coldstart.programmer_description({"id": "solo"})
        self.assertIn("NOT work outside solo.", solo)
        self.assertNotIn("(solo)", solo)
        zh_city = coldstart.programmer_description(by_id["city"], language="zh")
        self.assertIn("当用户点名 city", zh_city)
        self.assertIn("NOT new-city", zh_city)
        self.assertNotIn("（city）", zh_city)
        self.assertEqual(by_id["protocol"]["suggested_skill"], "")
        self.assertEqual(by_id["protocol"]["recommend"], "no")
        self.assertEqual(by_id["grab"]["suggested_skill"], "")
        self.assertEqual(by_id["grab"]["recommend"], "no")
        self.assertEqual(by_id["new-city"]["recommend"], "yes")
        self.assertTrue(by_id["new-city"]["suggested_skill"])
        self.assertEqual(by_id["city"]["recommend"], "no")
        self.assertTrue(by_id["city"]["suggested_skill"])

    def test_same_named_view_joins_feature_and_mechanism_splits(self):
        sources = {
            "Assets/Scripts/GameLogic/Logic/Modules/Chat/ChatRoom.cs": (
                "public class ChatRoom { void Open() { ChatWindow w = null; } }\n"
            ),
            "Assets/Scripts/GameLogic/Renderer/UI/Chat/ChatWindow.cs": (
                "public class ChatWindow {\n"
                "    void Show() { var a = new ChatRoom(); var b = new ChatRoom(); var c = new ChatRoom(); }\n"
                "}\n"
            ),
            "Assets/Scripts/GameLogic/Renderer/UI/Common/SharedRow.cs": (
                "public class SharedRow { }\n"
            ),
            "Assets/Scripts/Framework/Universal/UI/UIManager.cs": (
                "public class UIManager { void Open() { } }\n"
            ),
            "Assets/Scripts/Framework/Universal/Net/Socket.cs": (
                "public class Socket { void Send() { var u = new UIManager(); } }\n"
            ),
        }
        cards = _by_id(coldstart.analyze_sources(sources))
        chat_paths = " ".join(cards["chat"]["paths"])
        self.assertIn("Renderer/UI/Chat/ChatWindow.cs", chat_paths)
        self.assertNotIn("SharedRow", chat_paths)
        self.assertNotIn("UIManager", chat_paths)
        mechanism = cards["ui-mechanism"]
        self.assertIn("UIManager.cs", " ".join(mechanism["paths"]))
        self.assertNotIn("ChatWindow.cs", " ".join(mechanism["paths"]))
        self.assertEqual(mechanism["suggested_skill"], "")
        self.assertEqual(mechanism["recommend"], "no")
        self.assertNotIn("UIManager.cs", " ".join(cards["framework-universal"]["paths"]))


if __name__ == "__main__":
    unittest.main()
