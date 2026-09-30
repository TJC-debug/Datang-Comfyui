from pathlib import Path
import importlib.util
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "web" / "datang_group_switch.js").read_text(encoding="utf-8")


def load_group_module():
    spec = importlib.util.spec_from_file_location(
        "datang_group_switch", ROOT / "datang_group_switch.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DatangGroupSwitchTests(unittest.TestCase):
    def test_unified_package_registers_prompt_and_group_nodes_once(self):
        spec = importlib.util.spec_from_file_location(
            "datang_comfyui",
            ROOT / "__init__.py",
            submodule_search_locations=[str(ROOT)],
        )
        package = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = package
        try:
            spec.loader.exec_module(package)
        finally:
            sys.modules.pop(spec.name, None)
        self.assertEqual(package.__version__, "0.4.57")
        self.assertEqual(
            set(package.NODE_CLASS_MAPPINGS),
            {
                "PromptSwitchboard",
                "DatangRelightingPrompt",
                "DatangGroupSwitch",
                "DatangGroupPresenceMarker",
                "DatangBooleanNand",
                "DatangBooleanConstant",
                "DatangLazyIfElse",
                "DatangModelSelector",
                "NabeiPortraitComposition",
                "DatangQuickIdPhotoCrop",
                "DatangIdPhotoRatioCrop",
                "DatangImageSizeRestore",
                "DatangAspectCrop",
                "DatangPhotoPrintCrop",
                "DatangIdPhotoLayout",
                "DatangIdPhotoDpiSave",
                "DatangStageResultSave",
                "DatangFastFaceBeauty",
                "DatangBlemishRetouch",
            },
        )
        self.assertEqual(package.WEB_DIRECTORY, "./web")

    def test_backend_node_has_a_real_boolean_widget(self):
        module = load_group_module()
        inputs = module.DatangGroupSwitch.INPUT_TYPES()["required"]
        self.assertIn("启用节点组", inputs)
        self.assertEqual(inputs["启用节点组"][0], "BOOLEAN")
        self.assertEqual(module.DatangGroupSwitch().return_state(False), (False,))

    def test_frontend_uses_native_group_and_selected_canvas_nodes(self):
        self.assertIn("Object.values(this.selected_nodes || {})", SCRIPT)
        self.assertIn("new LiteGraph.LGraphGroup()", SCRIPT)
        self.assertIn("group.configure", SCRIPT)
        self.assertIn("group.recomputeInsideNodes", SCRIPT)
        self.assertIn("createDatangGroup(this, selectedNodes)", SCRIPT)
        self.assertIn("placeControllerInPsAiOrder", SCRIPT)
        self.assertIn('graph.extra.ps_ai.sort_mode = "manual"', SCRIPT)

    def test_plain_parameter_group_has_no_controller_or_switch_state(self):
        self.assertIn("createDatangParameterGroup(this, selectedNodes)", SCRIPT)
        self.assertIn("layoutParameterGroupForNodes(nodes)", SCRIPT)
        self.assertIn("writeDatangParameterGroupState(group)", SCRIPT)
        self.assertIn("selectedNodes.length < 2", SCRIPT)
        self.assertIn("设为无开关参数组", SCRIPT)

    def test_native_group_header_owns_the_visible_switch(self):
        self.assertIn("groupHeaderSwitchRect", SCRIPT)
        self.assertIn("drawHeaderSwitch", SCRIPT)
        self.assertIn("LGraphCanvas.prototype.drawGroups", SCRIPT)
        self.assertIn("pointInsideRect(event.canvasX, event.canvasY", SCRIPT)
        self.assertIn("readDatangGroupState(candidate)", SCRIPT)

    def test_internal_controller_is_hidden_but_kept_for_ps_ai_compatibility(self):
        self.assertIn("datang_embedded_controller", SCRIPT)
        self.assertIn("if (isEmbeddedController(node)) return", SCRIPT)
        self.assertIn("node.size = [1, 1]", SCRIPT)
        self.assertIn("writeDatangGroupState", SCRIPT)

    def test_group_creation_reserves_header_and_deletes_its_owned_controller(self):
        self.assertIn("groupBounds[index] = layout.bounding[index]", SCRIPT)
        self.assertIn("datang_delete_with_group", SCRIPT)
        self.assertIn("removeGroupOwnedController(node)", SCRIPT)
        self.assertIn("removeControllerFromOrder", SCRIPT)

    def test_controller_excludes_itself_and_controls_real_member_modes(self):
        self.assertIn("node !== controller", SCRIPT)
        self.assertIn("reconcileGroupModes", SCRIPT)
        self.assertIn("datang_previous_modes", SCRIPT)
        self.assertIn("widget.value === true", SCRIPT)
        self.assertIn("!isDatangGroupPresenceMarker(node)", SCRIPT)

    def test_presence_marker_stays_active_and_tracks_the_group_state(self):
        self.assertIn('PRESENCE_WIDGET_NAME = "组已启用"', SCRIPT)
        self.assertIn("findInnermostDatangGroupForNode", SCRIPT)
        self.assertIn("syncPresenceMarkersForGroup(group)", SCRIPT)
        self.assertIn("node.mode = 0", SCRIPT)
        self.assertIn('widget.type = "converted-widget"', SCRIPT)

    def test_controller_label_matches_the_ps_ai_group_contract(self):
        self.assertIn("widget.label = `Enable ${title}`", SCRIPT)
        self.assertIn("node.title = `${TITLE_PREFIX}${title}`", SCRIPT)
        self.assertIn("datang_group_title", SCRIPT)

    def test_ps_ai_can_request_a_real_canvas_group_state_change(self):
        self.assertIn('GROUP_SWITCH_REQUEST_EVENT = "datang-group-switch-request"', SCRIPT)
        self.assertIn("window.addEventListener(GROUP_SWITCH_REQUEST_EVENT, applyRequestedGroupState)", SCRIPT)
        self.assertIn("String(node.id) === String(controllerId)", SCRIPT)
        self.assertIn("groupController(group, graph, index) !== controller", SCRIPT)
        self.assertIn("applyControllerState(controller, widget, { index })", SCRIPT)

    def test_group_sync_uses_one_shared_index_and_avoids_high_frequency_full_scans(self):
        self.assertIn("indexDatangGroupControllers", SCRIPT)
        self.assertIn("refreshControllerIndex", SCRIPT)
        self.assertIn("writeGroupStateIfChanged", SCRIPT)
        self.assertIn("const SYNC_INTERVAL_MS = 1500", SCRIPT)


if __name__ == "__main__":
    unittest.main()
