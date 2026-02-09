#!/usr/bin/env python3
"""Generate enterprise-grade macOS app icon via DALL-E 3 HD."""

import sys

from sortmeout.integrations.images import ImageGenerator


def main():
    gen = ImageGenerator()
    print("Generating enterprise icon via DALL-E 3 HD...", flush=True)

    prompt = (
        "A premium macOS application icon for a file organization app. "
        "Ultra-polished 3D render in Apple macOS Sequoia icon style. "
        "Single macOS squircle (continuous rounded superellipse) shape. "
        "Inside: a sleek modern folder in rich deep teal gradient from "
        "dark teal at the bottom to bright cyan at the top. "
        "Integrated into the folder tab is a golden amber downward-pointing "
        "sorting arrow that glows softly, representing automated file organization. "
        "Apple-native design language. Soft top-down studio lighting. "
        "Gentle glass-like translucency on the folder surface. "
        "Subtle inner shadow. Clean ambient occlusion shadow beneath the squircle. "
        "Frosted glass texture. Photorealistic 3D render. "
        "Enterprise-grade premium SaaS product quality. "
        "No text, no letters, no words anywhere. Pure symbolic iconography. "
        "Should look indistinguishable from a first-party Apple app icon "
        "next to Finder, Safari, and Xcode in the macOS Dock. "
        "Think Things 3, Bear, or Fantastical app icon quality level. "
        "Background: solid dark charcoal (#1a1a1a) to make the icon pop."
    )

    try:
        result = gen.generate(
            prompt=prompt,
            size="1024x1024",
            quality="hd",
            style="natural",
            filename="sortmeout_icon_enterprise.png",
        )
        print(f"Success: {result.get('success')}")
        print(f"Path: {result.get('path')}")
        print(f"File size: {result.get('file_size')}")
        revised = result.get("revised_prompt", "")
        if revised:
            print(f"Revised prompt: {revised[:300]}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
