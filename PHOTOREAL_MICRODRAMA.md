# Photoreal AI Microdrama

Cartoon Studio V7 now includes a photoreal generation mode powered by MiniMax H3. The original Classic Cartoon, RealityBlend, Discovery Story, and Join Clips modes remain available.

## Pipeline

1. Add a clear reference image for each recurring human character.
2. Describe the character identity and appearance.
3. Build scenes with setting, characters, action/camera direction, exact dialogue, and 4–15 second duration.
4. Cartoon Studio sends each scene to MiniMax H3 reference-to-video.
5. MiniMax returns a task ID; the app polls until the clip is complete.
6. The app downloads each clip, previews it, stitches the episode, and can burn dialogue captions into the final MP4.

MiniMax H3 currently supports reference-to-video with up to 9 reference images, 4–15 second clips, 768P or 2K output, and multiple aspect ratios. H3 also generates native audio. H3-Max is intentionally not enabled for this recurring-character workflow because it does not support reference-to-video.

## API key

Set `MINIMAX_API_KEY` in Streamlit secrets or the deployment environment. For local development, copy `.env.example` to `.env` and load the variable through your preferred environment manager.

The global API base defaults to `https://api.minimax.io` and can be changed with `MINIMAX_API_BASE`.

## Reference images

Public HTTPS image URLs are recommended. The engine also supports uploaded images as data URLs for small references; MiniMax documents a 64 MB total request-body limit and recommends public URLs for large media.

## Important generation rule

Dialogue must be entered verbatim. Do not give a summary such as `she explains why she is angry`; enter the exact sentence you want spoken. The scene prompt tells H3 to preserve the words and synchronize the character's mouth and expression to the dialogue.

## Cost control

Generate a single 4–6 second 768P scene first. Current MiniMax H3 pricing is listed by MiniMax at $0.08/second for 768P video and $0.13/second for 2K video. Actual account billing and future pricing can differ, so treat this as an estimate and verify the current MiniMax pricing page before large batches.

## Deployment

The app still uses the existing Docker/Streamlit deployment. The photoreal renderer does not require Blender. FFmpeg remains used for local stitching/caption processing after MiniMax returns the clips.
