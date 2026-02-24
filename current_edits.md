# 🌐 Project: 2080 Urban Panoramas

### 🚧 The Core Challenge: Panoramic Consistency
Maintaining visual continuity across a 360° view is difficult because standard AI models are "stateless"—they don't remember what they drew in the previous frame. This results in "visual drift" where colors, building heights, and textures don't align at the edges.

### 🛠️ Strategic Approaches

| Method | Status | Pros/Cons |
| :--- | :--- | :--- |
| **1. Video Generation** | *Future Phase* | **Pros:** Native temporal consistency. **Cons:** Harder to control specific architectural details. |
| **2. Direct Panorama Editing** | *Future Phase* | **Pros:** 1:1 pixel alignment across edges. **Cons:** Requires specialized out-painting tools and high compute. |
| **3. Logical Synchronization** | **CURRENT** | **Pros:** Maintains consistent world-rules across independent calls. **Cons:** Slight edge-alignment variance. |

---

### 💡 Our Current Method (Option 3)
Since we are generating images individually, we use the LLM as a **"Central Urban Planner"** to enforce consistency:
1.  **360° Analysis:** The LLM scans all panorama segments at once to identify continuous elements (roads, skylines, shared buildings).
2.  **Universal State Generation:** A master "2080 World State" is created, defining specific materials, color palettes, and tech retrofits.
3.  **Prompt Anchoring:** This master description is injected into every separate generation call. This ensures that even if the pixels aren't perfectly joined, the **logic, lighting, and style** are identical.

---

### 🌍 2080 Future Predictions
These "Future States" are used as the logic-base for all image generations:

**1. San Diego (Coronado) | "The Sponge City"**
* **Transformation:** Shift from high-traffic tourism to a carbon-negative coastal buffer.
* **Key Changes:** Salt-marsh "Sponge Parks" for flood defense, autonomous water-taxis, and solar-active film on Mediterranean facades.

**2. Staithes, UK | "The Lithic Shipyard"**
* **Transformation:** Historic harbor turned into a high-tech, camouflaged maritime industrial hub.
* **Key Changes:** Graphene-mesh cliff stabilization, 3D-printed wave-breakers, and stealth hull synthesis in submerged docks.

**3. Everest (Khumbu) | "The Cryo-Shelter"**
* **Transformation:** High-altitude survival colony and atmospheric research hub.
* **Key Changes:** Sapphire-glass solar roofs, pressurized geodesic greenhouses on ancient terraces, and permafrost thermal anchors.

---

### 📝 Global Prompt Seed (Source of Truth)
*Every image generation uses these constraints to ensure a unified look:*
* **Materials:** Recycled sea-glass, carbon-fiber, graphene-mesh, sapphire photovoltaics.
* **Infrastructure:** Kinetic pavers, bioluminescent safety lighting, autonomous transit ribbons.
* **Palette:** Matte Terra Cotta, Salt-Washed White, Deep Shale Grey, Bio-Cyan accents.