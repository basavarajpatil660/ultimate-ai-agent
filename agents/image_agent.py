import os
import requests
import time
import urllib.parse

def generate_image(
    prompt,
    CLOUDFLARE_WORKER_URL=None,
    CLOUDFLARE_API_KEY=None,
    PIXAZO_API_KEY=None
):

    # Truncate prompt to safe length
    prompt = prompt[:500] if prompt else "abstract art"
    
    # Provider 1: Cloudflare Worker
    if CLOUDFLARE_WORKER_URL:
        try:
            url = CLOUDFLARE_WORKER_URL.rstrip("/") + "/generate"
            headers = {"Content-Type": "application/json"}
            if CLOUDFLARE_API_KEY:
                headers["Authorization"] = f"Bearer {CLOUDFLARE_API_KEY}"
            response = requests.post(
                url,
                headers=headers,
                json={"prompt": prompt},
                timeout=60
            )
            print(f"Cloudflare status: {response.status_code}")
            if response.status_code == 200:
                content = response.content
                if len(content) > 1000:
                    with open("/tmp/output.png", "wb") as f:
                        f.write(content)
                    print("Image generated via Cloudflare FLUX")
                    return {
                        "file_path": "/tmp/output.png",
                        "provider": "cloudflare"
                    }
                else:
                    print(f"Cloudflare returned too small: {len(content)} bytes")
                    print(f"Response text: {response.text[:200]}")
            else:
                print(f"Cloudflare error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"Cloudflare exception: {e}")

    # Provider 2: ModelsLab
    MODELSLAB_API_KEY = os.environ.get(
        "MODELSLAB_API_KEY", None)
    if MODELSLAB_API_KEY:
        try:
            response = requests.post(
                "https://modelslab.com/api/v6/realtime/text2img",
                headers={"Content-Type": "application/json"},
                json={
                    "key": MODELSLAB_API_KEY,
                    "prompt": prompt,
                    "negative_prompt": "blurry, bad quality, distorted",
                    "width": "512",
                    "height": "512",
                    "safety_checker": False,
                    "seed": None,
                    "samples": 1,
                    "base64": False,
                    "webhook": None,
                    "track_id": None
                },
                timeout=60
            )
            print(f"ModelsLab status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                if status == "success":
                    img_url = data.get("output", [None])[0]
                    if img_url:
                        img_res = requests.get(
                            img_url, timeout=30)
                        if img_res.status_code == 200:
                            with open("/tmp/output.png", "wb") as f:
                                f.write(img_res.content)
                            print("Image generated via ModelsLab")
                            return {
                                "file_path": "/tmp/output.png",
                                "provider": "modelslab"
                            }
                elif status == "processing":
                    import time
                    eta = data.get("eta", 10)
                    fetch_url = data.get("fetch_result")
                    print(f"ModelsLab processing, ETA {eta}s")
                    time.sleep(min(eta + 5, 30))
                    if fetch_url:
                        fetch_res = requests.post(
                            fetch_url,
                            headers={
                                "Content-Type": "application/json"
                            },
                            json={"key": MODELSLAB_API_KEY},
                            timeout=30
                        )
                        if fetch_res.status_code == 200:
                            fetch_data = fetch_res.json()
                            img_url = fetch_data.get(
                                "output", [None])[0]
                            if img_url:
                                img_res = requests.get(
                                    img_url, timeout=30)
                                if img_res.status_code == 200:
                                    with open("/tmp/output.png","wb") as f:
                                        f.write(img_res.content)
                                    print("Image via ModelsLab (fetched)")
                                    return {
                                        "file_path": "/tmp/output.png",
                                        "provider": "modelslab"
                                    }
                else:
                    print(f"ModelsLab error: {data}")
        except Exception as e:
            print(f"ModelsLab failed: {e}")
    else:
        print("ModelsLab key not set, skipping")

    # Provider 3: Pixazo
    if PIXAZO_API_KEY:
        try:
            response = requests.post(
                "https://api-console.pixazo.ai/v1/generate",
                headers={
                    "Authorization": f"Bearer {PIXAZO_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "model": "flux-schnell"
                },
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                img_url = data.get("image_url") or \
                          data.get("url") or \
                          data.get("output")
                if img_url:
                    img_response = requests.get(
                        img_url, timeout=30)
                    if img_response.status_code == 200:
                        with open("/tmp/output.png", "wb") as f:
                            f.write(img_response.content)
                        print("Image generated via Pixazo")
                        return {
                            "file_path": "/tmp/output.png",
                            "provider": "pixazo"
                        }
        except Exception as e:
            print(f"Pixazo image failed: {e}")

    print("All image providers failed")
    return None
