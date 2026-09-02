"""REG-0030: real Tuanjie compilation and metadata verification for ASECLI GUI."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import textwrap

import pytest

from asecli.bridge.gui_support import GUI_SUPPORT_ASSET_PATH, install_gui_support


PROJECT_ENV = "ASECLI_GUI_TEST_PROJECT"
EDITOR_ENV = "ASECLI_TUANJIE_PATH"
MARKER = ".asecli-gui-e2e-isolated"
ROOT = "Assets/ASECLIGUIE2E"


@pytest.mark.bridge
def test_real_tuanjie_gui_compiles_and_reads_new_and_legacy_metadata():
    project_raw = os.environ.get(PROJECT_ENV)
    editor_raw = os.environ.get(EDITOR_ENV)
    if not project_raw or not editor_raw:
        pytest.skip(f"set {PROJECT_ENV} and {EDITOR_ENV} to run the real Tuanjie GUI gate")

    project = Path(project_raw).resolve()
    editor = Path(editor_raw).resolve()
    assert (project / MARKER).is_file(), "refusing Editor writes without isolated-project marker"
    assert (project / "Assets").is_dir() and (project / "ProjectSettings").is_dir()
    assert editor.is_file(), f"Tuanjie executable not found: {editor}"
    target_root = project / ROOT
    assert not target_root.exists(), f"refusing to reuse GUI E2E assets: {target_root}"

    installed = install_gui_support(project, write=True)
    assert installed["written"] is True
    assert (project / GUI_SUPPORT_ASSET_PATH).is_file()

    target_root.mkdir(parents=True)
    (target_root / "NewMarkers.shader").write_text(_shader("ASECLI"), encoding="utf-8")
    (target_root / "LegacyMarkers.shader").write_text(_shader("legacy"), encoding="utf-8")
    editor_dir = target_root / "Editor"
    editor_dir.mkdir()
    (editor_dir / "ASECLIMaterialGUIE2E.cs").write_text(_harness_source(), encoding="utf-8")

    log = project / "asecli-material-gui-e2e.log"
    proc = subprocess.run(
        [
            str(editor), "-batchmode", "-nographics", "-projectPath", str(project),
            "-executeMethod", "ASECLIMaterialGUIE2E.Run", "-logFile", str(log),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    tail = log.read_text(encoding="utf-8", errors="replace")[-12000:] if log.exists() else proc.stderr[-12000:]
    assert proc.returncode == 0, tail
    assert (project / "asecli-material-gui-e2e-result.txt").read_text(encoding="utf-8") == "OK\n"
    assert not any(marker in tail for marker in ("error CS", "Shader error", "failed to compile", "Exception:"))


def _shader(kind: str) -> str:
    if kind == "ASECLI":
        attributes = "[ASECLIFoldout(New Group)] [ASECLITooltip(New tooltip)] [ASECLIHelpBox(New help text)]"
        name = "ASECLI/E2E/NewMarkers"
    else:
        attributes = "[FoldoutMzgui(Legacy Group)] [TooltipMzgui(Legacy tooltip)] [HelpBoxMzgui(Legacy help text)]"
        name = "ASECLI/E2E/LegacyMarkers"
    return f'''Shader "{name}"
{{
    Properties
    {{
        {attributes} _Value("Value", Float) = 1.25
        _Followup("Followup", Float) = 0.5
    }}
    SubShader
    {{
        Pass
        {{
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            float _Value;
            float _Followup;
            struct appdata {{ float4 vertex : POSITION; }};
            struct v2f {{ float4 pos : SV_POSITION; }};
            v2f vert(appdata v) {{ v2f o; o.pos = UnityObjectToClipPos(v.vertex); return o; }}
            fixed4 frag(v2f i) : SV_Target {{ return fixed4(_Value, _Followup, 0, 1); }}
            ENDCG
        }}
    }}
    CustomEditor "ASECLI.MaterialGUI.ASECLIMaterialGUI"
}}
'''


def _harness_source() -> str:
    return textwrap.dedent(
        '''\
        using System;
        using System.Collections;
        using System.Reflection;
        using ASECLI.MaterialGUI;
        using UnityEditor;
        using UnityEngine;

        public static class ASECLIMaterialGUIE2E
        {
            public static void Run()
            {
                try
                {
                    AssetDatabase.Refresh();
                    Verify("Assets/ASECLIGUIE2E/NewMarkers.shader", "New Group", "New tooltip", "New help text", "ASECLI");
                    Verify("Assets/ASECLIGUIE2E/LegacyMarkers.shader", "Legacy Group", "Legacy tooltip", "Legacy help text", "Mzgui");
                    System.IO.File.WriteAllText("asecli-material-gui-e2e-result.txt", "OK\\n");
                    EditorApplication.Exit(0);
                }
                catch (Exception exception)
                {
                    System.IO.File.WriteAllText("asecli-material-gui-e2e-result.txt", "FAIL\\n" + exception);
                    Debug.LogException(exception);
                    EditorApplication.Exit(1);
                }
            }

            private static void Verify(string path, string foldout, string tooltip, string help, string decoratorToken)
            {
                Shader shader = AssetDatabase.LoadAssetAtPath<Shader>(path);
                if (shader == null) throw new Exception("missing shader: " + path);
                MethodInfo hasError = typeof(ShaderUtil).GetMethod("ShaderHasError", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static, null, new[] { typeof(Shader) }, null);
                if (hasError != null && Convert.ToBoolean(hasError.Invoke(null, new object[] { shader }))) throw new Exception("shader compile error: " + path);
                Material material = new Material(shader);
                try
                {
                    MaterialEditor.GetMaterialProperties(new UnityEngine.Object[] { material });
                    Type gui = typeof(ASECLIMaterialGUI);
                    MethodInfo readMetadata = gui.GetMethod("ReadMetadata", BindingFlags.NonPublic | BindingFlags.Static);
                    IDictionary metadata = (IDictionary)readMetadata.Invoke(null, new object[] { shader });
                    object valueMetadata = metadata["_Value"];
                    if (valueMetadata == null) throw new Exception("metadata missing: " + path);
                    Type metadataType = valueMetadata.GetType();
                    Require(metadataType.GetField("Foldout", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance).GetValue(valueMetadata) as string, foldout, "foldout");
                    Require(metadataType.GetField("Tooltip", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance).GetValue(valueMetadata) as string, tooltip, "tooltip");
                    Require(metadataType.GetField("Help", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance).GetValue(valueMetadata) as string, help, "help");
                    MethodInfo readDefaults = gui.GetMethod("ReadDefaultValues", BindingFlags.NonPublic | BindingFlags.Static);
                    Require(((IDictionary)readDefaults.Invoke(null, new object[] { shader }))["_Value"] as string, "1.25", "default");
                    VerifyDecorator(shader, decoratorToken);
                }
                finally { UnityEngine.Object.DestroyImmediate(material); }
            }

            private static void VerifyDecorator(Shader shader, string token)
            {
                Type handlerType = typeof(MaterialEditor).Assembly.GetType("UnityEditor.MaterialPropertyHandler");
                MethodInfo getHandler = handlerType.GetMethod("GetHandler", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static, null, new[] { typeof(Shader), typeof(string) }, null);
                FieldInfo decorators = handlerType.GetField("m_DecoratorDrawers", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                bool found = false;
                foreach (object drawer in decorators.GetValue(getHandler.Invoke(null, new object[] { shader, "_Value" })) as IEnumerable)
                    if (drawer != null && drawer.GetType().Name.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0) found = true;
                if (!found) throw new Exception("decorator not instantiated: " + token);
                if (String.Equals(token, "Mzgui", StringComparison.OrdinalIgnoreCase))
                {
                    bool nativeCollision = false;
                    foreach (object drawer in decorators.GetValue(getHandler.Invoke(null, new object[] { shader, "_Value" })) as IEnumerable)
                        if (drawer != null && drawer.GetType().FullName.StartsWith("MZGUI.", StringComparison.Ordinal)) nativeCollision = true;
                    if (!nativeCollision) throw new Exception("legacy drawer collision was not reproduced");
                }
            }

            private static void Require(string actual, string expected, string label)
            {
                if (!String.Equals(actual, expected, StringComparison.Ordinal))
                    throw new Exception(label + " expected '" + expected + "' but got '" + actual + "'");
            }
        }

        // Emulates a project that already contains the legacy MZGUI drawers.
        // The fallback must therefore not rely on the ASECLI shim winning Unity's
        // unqualified drawer lookup.
        namespace MZGUI
        {
            public sealed class FoldoutMzguiDecorator : UnityEditor.MaterialPropertyDrawer
            {
                public FoldoutMzguiDecorator() { }
                public FoldoutMzguiDecorator(string value) { }
                public override float GetPropertyHeight(UnityEditor.MaterialProperty prop, string label, UnityEditor.MaterialEditor editor) { return 0f; }
                public override void OnGUI(UnityEngine.Rect position, UnityEditor.MaterialProperty prop, UnityEngine.GUIContent label, UnityEditor.MaterialEditor editor) { }
            }

            public sealed class TooltipMzguiDecorator : UnityEditor.MaterialPropertyDrawer
            {
                public TooltipMzguiDecorator() { }
                public TooltipMzguiDecorator(string value) { }
                public override float GetPropertyHeight(UnityEditor.MaterialProperty prop, string label, UnityEditor.MaterialEditor editor) { return 0f; }
                public override void OnGUI(UnityEngine.Rect position, UnityEditor.MaterialProperty prop, UnityEngine.GUIContent label, UnityEditor.MaterialEditor editor) { }
            }

            public sealed class HelpBoxMzguiDecorator : UnityEditor.MaterialPropertyDrawer
            {
                public HelpBoxMzguiDecorator() { }
                public HelpBoxMzguiDecorator(string value) { }
                public override float GetPropertyHeight(UnityEditor.MaterialProperty prop, string label, UnityEditor.MaterialEditor editor) { return 0f; }
                public override void OnGUI(UnityEngine.Rect position, UnityEditor.MaterialProperty prop, UnityEngine.GUIContent label, UnityEditor.MaterialEditor editor) { }
            }
        }
        '''
    )
