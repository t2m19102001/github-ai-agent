#!/usr/bin/env python3
"""
Create a prebuilt VSIX package for the GitHub AI Agent VS Code Extension
without requiring Node.js or npm installation.
"""

import os
import json
import shutil
import zipfile
from pathlib import Path


def create_vsix_package():
    """Create a VSIX package from the extension source files."""
    
    project_root = Path(__file__).parent
    ext_dir = project_root / "vscode-extension"
    vsix_dir = ext_dir / "vsix_build"
    
    # Clean previous build
    if vsix_dir.exists():
        shutil.rmtree(vsix_dir)
    vsix_dir.mkdir(parents=True)
    
    # Copy necessary files
    print("📦 Preparing VSIX structure...")
    
    # Copy TypeScript source files (compiled to JS in the VSIX)
    src_dir = vsix_dir / "out"
    src_dir.mkdir()
    
    # Read and process extension.ts
    ext_ts = (ext_dir / "src" / "extension.ts").read_text()
    ext_js = convert_ts_to_js(ext_ts)
    (src_dir / "extension.js").write_text(ext_js)
    
    # Copy commands
    commands_dir = src_dir / "commands"
    commands_dir.mkdir()
    for cmd_file in (ext_dir / "src" / "commands").glob("*.ts"):
        ts_code = cmd_file.read_text()
        js_code = convert_ts_to_js(ts_code)
        (commands_dir / cmd_file.stem).with_suffix(".js").write_text(js_code)
    
    # Copy panels
    panels_dir = src_dir / "panels"
    panels_dir.mkdir()
    for panel_file in (ext_dir / "src" / "panels").glob("*.ts"):
        ts_code = panel_file.read_text()
        js_code = convert_ts_to_js(ts_code)
        (panels_dir / panel_file.stem).with_suffix(".js").write_text(js_code)
    
    # Copy providers
    providers_dir = src_dir / "providers"
    providers_dir.mkdir()
    for provider_file in (ext_dir / "src" / "providers").glob("*.ts"):
        ts_code = provider_file.read_text()
        js_code = convert_ts_to_js(ts_code)
        (providers_dir / provider_file.stem).with_suffix(".js").write_text(js_code)
    
    # Copy services
    services_dir = src_dir / "services"
    services_dir.mkdir()
    for service_file in (ext_dir / "src" / "services").glob("*.ts"):
        ts_code = service_file.read_text()
        js_code = convert_ts_to_js(ts_code)
        (services_dir / service_file.stem).with_suffix(".js").write_text(js_code)
    
    # Copy UI
    ui_dir = src_dir / "ui"
    ui_dir.mkdir()
    for ui_file in (ext_dir / "src" / "ui").glob("*.ts"):
        ts_code = ui_file.read_text()
        js_code = convert_ts_to_js(ts_code)
        (ui_dir / ui_file.stem).with_suffix(".js").write_text(js_code)
    
    # Copy package.json
    package_json = (ext_dir / "package.json").read_text()
    (vsix_dir / "package.json").write_text(package_json)
    
    # Copy README and other files
    for file in ["README.md", "LICENSE", "CHANGELOG.md"]:
        src = ext_dir / file
        if src.exists():
            shutil.copy(src, vsix_dir / file)
    
    # Create icon directory
    icon_dir = vsix_dir / "media"
    icon_dir.mkdir()
    icon_src = ext_dir / "media"
    if icon_src.exists():
        for icon_file in icon_src.glob("*"):
            shutil.copy(icon_file, icon_dir / icon_file.name)
    
    # Create .vscodeignore
    (vsix_dir / ".vscodeignore").write_text(
        "node_modules/\n"
        ".vscode/\n"
        "out/test/\n"
        "src/\n"
        "*.ts\n"
        "*.map\n"
        ".gitignore\n"
        "vsc-extension-quickstart.md\n"
        "**/*.spec.ts\n"
    )
    
    # Create VSIX (which is just a ZIP file)
    vsix_file = ext_dir / "github-ai-extension.vsix"
    print(f"📝 Creating VSIX package: {vsix_file}")
    
    with zipfile.ZipFile(vsix_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(vsix_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(vsix_dir)
                zf.write(file_path, arcname)
    
    print(f"✅ VSIX package created: {vsix_file}")
    print(f"📊 Size: {vsix_file.stat().st_size / 1024:.2f} KB")
    
    # Cleanup
    shutil.rmtree(vsix_dir)
    
    return vsix_file


def convert_ts_to_js(ts_code):
    """Simple TypeScript to JavaScript conversion for basic patterns."""
    
    js_code = ts_code
    
    # Remove TypeScript type annotations
    # import { X }: Y => import { X }
    import re
    js_code = re.sub(r'import\s+{([^}]+)}:\s+["\']([^"\']+)["\']', r'import { \1 } from "\2"', js_code)
    
    # Remove type definitions: variable: Type => variable
    js_code = re.sub(r'(\w+):\s+(?:string|number|boolean|any|void|Promise<[^>]+>|[A-Z]\w+(?:<[^>]+>)?)\s*[;,=]', r'\1;', js_code)
    
    # Remove interface/type declarations
    js_code = re.sub(r'(?:interface|type)\s+\w+\s*(?:extends|=)?[^{]*{[^}]*}', '', js_code, flags=re.DOTALL)
    
    # Remove as declarations
    js_code = re.sub(r'\s+as\s+\w+(?:<[^>]+>)?(?=[,;\)])', '', js_code)
    
    # Remove generic types
    js_code = re.sub(r'<[^>]+>', '', js_code)
    
    # Keep import/export statements
    lines = js_code.split('\n')
    result_lines = []
    
    for line in lines:
        # Skip empty interface/type definitions
        if line.strip().startswith(('interface ', 'type ')):
            continue
        result_lines.append(line)
    
    return '\n'.join(result_lines)


if __name__ == "__main__":
    try:
        vsix_file = create_vsix_package()
        print("\n" + "=" * 60)
        print("🎉 SUCCESS!")
        print("=" * 60)
        print(f"\nVSIX package ready at:")
        print(f"  {vsix_file}")
        print("\nTo install in VS Code:")
        print("  1. Open VS Code")
        print("  2. Go to Extensions")
        print("  3. Click ... → Install from VSIX")
        print("  4. Select the VSIX file")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
