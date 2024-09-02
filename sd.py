import requests
import json
import shutil

tokens = json.loads(
    open("token.json", "r").read()
)

headers = {"Authorization": tokens['hf_token']}


def query(prompt, api_url, save_location, seed):
    response = requests.post(api_url, headers=headers, json={
        "inputs": prompt,
        "seed": seed
    })
    if str(response.status_code)[0] != "2":
        # Clone oops.png into the save location
        source = "./oops.png"
        shutil.copy(source, save_location)
        print(response.content)
        return {
            "status_code": response.status_code,
        }
    import io
    from PIL import Image
    image = Image.open(io.BytesIO(response.content))
    image.save(save_location)
    return None
