import torch, random
from scene_card import normalize, scene_card
from datetime import datetime

def scene_card_to_template_prompt(card):
    e = card["map_context"]["elements"]
    w = card["weather"]["condition"]
    sun = card["sun"]
    style = "photorealistic street-level photo, 35mm lens, natural colors"

    parts = [
      card["prompt"],  # your deterministic sentence
      f"weather: {w}",
      f"time: {'night' if sun['is_night'] else 'day'}",
      f"dominant road: {e.get('road_type','residential')}",
      "sidewalk present" if e.get("sidewalk") else "no visible sidewalk",
      f"buildings: {e.get('building_height_hint','unknown')} density {e.get('building_density','medium')}",
      style
    ]
    return ", ".join(p for p in parts if p)


dt = datetime(2025, 11, 26, 17, 0, 0)  # UTC
weather = {"label": "overcast", "temp_c": 7.4, "wind_mps": 3.1, "precip_mm": 0.0, "visibility_km": 8.0}

norm = normalize(48.85837, 2.29448, dt, weather)
card = scene_card(norm)
prompt = scene_card_to_prompt(card)

neg = "lowres, overexposed, artifacts, text, watermark, fisheye, distorted perspective"

seed = 1234
g = torch.Generator("cuda").manual_seed(seed)
img = pipe(prompt=prompt, negative_prompt=neg, num_inference_steps=30,
           guidance_scale=5.5, height=1024, width=1024, generator=g).images[0]
img.save("out_text_only.png")

