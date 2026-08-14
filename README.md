# Cartoon Studio V1.1

Beginner-friendly Streamlit web app for creating simple 2D cartoon videos and joining short videos into one longer MP4.

## Deploy to Streamlit Community Cloud

Upload these files to your GitHub repository:
- app.py
- requirements.txt
- packages.txt
- README.md

`packages.txt` installs FFmpeg, which is required for video creation and joining.

Then connect the GitHub repository to Streamlit Community Cloud and select `app.py`.

## Run locally

Install FFmpeg and Python dependencies:

```bash
pip install -r requirements.txt
streamlit run app.py
```
