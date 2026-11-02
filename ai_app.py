import os
import sys

# Automatically determine where the program is running
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

# Select drive for heavy models (D:\ if exists, otherwise project folder)
if os.path.exists("D:\\"):
    AI_BASE_DIR = r"D:\ai_models"
else:
    AI_BASE_DIR = os.path.join(BASE_DIR, "ai_models")

# Define Hugging Face home directory for Stable Diffusion weights
os.environ["HF_HOME"] = os.path.join(AI_BASE_DIR, "huggingface")
os.makedirs(os.environ["HF_HOME"], exist_ok=True)

import requests
import base64
import re
import torch
import random
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter.filedialog import askopenfilename
from diffusers import StableDiffusionImg2ImgPipeline

OLLAMA_URL = "http://localhost:11434/api/generate"
MEMORY_FILE = os.path.join(AI_BASE_DIR, "ai_memory.txt")

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class StillLifeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Memory Mutator: Still Life")
        self.geometry("1100x650")

        self.input_path = None
        self.output_path = os.path.join(AI_BASE_DIR, "output_still_life.jpg")
        self.pipe = None

        # --- LEFT PANEL (Controls) ---
        self.left_frame = ctk.CTkFrame(self, width=300, corner_radius=10)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10, expand=False)

        self.btn_select = ctk.CTkButton(self.left_frame, text="Select Photo", command=self.select_image, height=40)
        self.btn_select.pack(fill="x", padx=20, pady=20)

        self.btn_start = ctk.CTkButton(self.left_frame, text="MUTATE PHOTO", command=self.start_process, fg_color="darkred", hover_color="red", height=50)
        self.btn_start.pack(fill="x", padx=20, pady=10)

        self.log_text = ctk.CTkTextbox(self.left_frame, height=200)
        self.log_text.pack(fill="x", padx=20, pady=20)
        self.log("System Ready.\nPlease select an image.")

        self.feedback_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.btn_good = ctk.CTkButton(self.feedback_frame, text="👍 Awesome", command=lambda: self.feedback(1), fg_color="green")
        self.btn_bad = ctk.CTkButton(self.feedback_frame, text="👎 Meh", command=lambda: self.feedback(0), fg_color="gray")

        # --- RIGHT PANEL (Previews) ---
        self.right_frame = ctk.CTkFrame(self, corner_radius=10)
        self.right_frame.pack(side="right", fill="both", padx=10, pady=10, expand=True)

        self.lbl_orig = ctk.CTkLabel(self.right_frame, text="Original Photo Preview", width=380, height=380)
        self.lbl_orig.pack(side="left", padx=20, pady=20, expand=True)

        self.lbl_result = ctk.CTkLabel(self.right_frame, text="Mutated Memory Result", width=380, height=380)
        self.lbl_result.pack(side="right", padx=20, pady=20, expand=True)

        self.current_prompt = ""
        self.current_strength = 0.6

    def log(self, message):
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.update()

    def select_image(self):
        file_path = askopenfilename(filetypes=[("Images", "*.jpg;*.jpeg;*.png")])
        if file_path:
            self.input_path = file_path
            img = Image.open(file_path).resize((380, 380))
            ctk_img = ctk.CTkImage(light_image=img, size=(380, 380))
            self.lbl_orig.configure(image=ctk_img, text="")
            self.log(f"Loaded image: {os.path.basename(file_path)}")

    def load_memory(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            except:
                pass
        return "No past experience yet."

    def ask_llava(self, past_memory):
        with open(self.input_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = f"""
        Look at this image. We want to mutate it into a decayed 'Still Life' painting, where objects melt and warp.
        Past training memory: {past_memory}
        
        Write exactly a prompt and a strength value. Follow format:
        PROMPT: [3-5 words in English describing mutation, e.g. melting cat, glitch oil painting]
        STRENGTH: [number from 0.4 to 0.8]
        """
        try:
            res = requests.post(OLLAMA_URL, json={
                "model": "llava",
                "prompt": prompt,
                "images": [img_b64],
                "stream": False
            }, timeout=30)
            response_text = res.json().get("response", "").strip()

            p_match = re.search(r"PROMPT:\s*(.*)", response_text, re.IGNORECASE)
            s_match = re.search(r"STRENGTH:\s*([0-9.]+)", response_text, re.IGNORECASE)

            ai_prompt = p_match.group(1).strip() if p_match else "melting distorted art, decay"
            strength = float(s_match.group(1).strip()) if s_match else 0.6
            return ai_prompt, max(0.4, min(strength, 0.85))
        except Exception as e:
            self.log("⚠️ Llava AI didn't respond. Using baseline presets.")
            return "melting corrupted portrait, still life decay", 0.6

    def start_process(self):
        if not self.input_path:
            self.log("❌ Please select a photo first!")
            return

        self.btn_start.configure(state="disabled", text="AI is Thinking...")
        self.log("\n🧠 AI is scanning the image...")

        memory = self.load_memory()
        ai_prompt, strength = self.ask_llava(memory)
        self.current_prompt = ai_prompt
        self.current_strength = strength

        self.log(f"⚙️ AI Prompt Choice: {ai_prompt}")
        self.log(f"⚙️ Mutation Strength: {strength}")

        if self.pipe is None:
            self.log("🎨 Loading Stable Diffusion weights...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model_id = "runwayml/stable-diffusion-v1-5"

            self.pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
                model_id, 
                torch_dtype=torch.float32 if device == "cpu" else torch.float16
            )

            # Deactivate Safety Checker to stop getting pure black screens
            self.pipe.safety_checker = None
            self.pipe.requires_safety_checker = False
            self.pipe = self.pipe.to(device)

        self.log("🚀 Mutating shapes and textures...")

        init_image = Image.open(self.input_path).convert("RGB").resize((512, 512))

        with torch.inference_mode():
            output = self.pipe(
                prompt=ai_prompt, 
                image=init_image, 
                strength=strength, 
                guidance_scale=7.5
            )

        final_image = output.images[0]
        final_image.save(self.output_path)

        result_img = Image.open(self.output_path).resize((380, 380))
        ctk_result = ctk.CTkImage(light_image=result_img, size=(380, 380))
        self.lbl_result.configure(image=ctk_result, text="")

        self.log("🖼️ Done! Mutation output loaded.")
        self.log("Rate this result to train the AI:")

        self.feedback_frame.pack(fill="x", padx=20, pady=10)
        self.btn_good.pack(side="left", expand=True, padx=5)
        self.btn_bad.pack(side="right", expand=True, padx=5)

        self.btn_start.configure(state="normal", text="MUTATE PHOTO")

    def feedback(self, score):
        if score == 1:
            try:
                with open(MEMORY_FILE, "a", encoding="utf-8") as f:
                    f.write(f"Style success: prompt='{self.current_prompt}' with strength {self.current_strength}\n")
                self.log("🧠 Saved successfully to AI neural memory!")
            except Exception as e:
                self.log(f"Error updating memory: {e}")
        else:
            self.log("📉 AI will avoid this mutation logic in the future.")
        
        self.feedback_frame.pack_forget()

if __name__ == "__main__":
    app = StillLifeApp()
    app.mainloop()
