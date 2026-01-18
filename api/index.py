from flask import Flask, render_template_string, jsonify
import google.generativeai as genai
from github import Github
import os
import random
import datetime

app = Flask(__name__)

# Konfigurasi API Helper
def get_gemini_response(prompt):
    try:
        # Pastikan Environment Variable GEMINI_API_KEY sudah diset di Vercel
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        # Menggunakan model flash yang cepat dan efisien
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        # Bersihkan markdown formatting dari output AI
        return response.text.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        return f"<!-- AI ERROR: {str(e)} -->"

@app.route('/')
def home():
    try:
        # Saat user akses web, ambil file HTML terbaru langsung dari GitHub
        # Ini memastikan user selalu melihat versi evolusi terakhir
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(os.getenv("REPO_NAME"))
        content = repo.get_contents("templates/index.html").decoded_content.decode("utf-8")
        return render_template_string(content)
    except Exception as e:
        # Fallback jika GitHub down atau token salah
        return f"<h1>COS-X SYSTEM BOOTING...</h1><p>Error: {str(e)}</p>"

@app.route('/api/evolve_trigger', methods=['GET'])
def evolve():
    try:
        # Koneksi ke GitHub
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(os.getenv("REPO_NAME"))
        
        # 1. Ambil DNA (HTML) saat ini
        try:
            file_html = repo.get_contents("templates/index.html")
            current_html = file_html.decoded_content.decode("utf-8")
            sha_html = file_html.sha
        except:
            current_html = "<html><body><h1>GENESIS</h1></body></html>"
            sha_html = None

        # 2. Cek apakah ada instruksi manual dari Builder (instructions.txt)
        mode = "Auto"
        user_instruction = ""
        sha_instr = None
        
        try:
            file_instr = repo.get_contents("instructions.txt")
            content_instr = file_instr.decoded_content.decode("utf-8").strip()
            sha_instr = file_instr.sha
            # Jika file tidak kosong dan bukan pesan system 'Done', jalankan mode Manual
            if content_instr and "System: Done" not in content_instr and len(content_instr) > 5:
                mode = "Manual"
                user_instruction = content_instr
        except:
            pass

        # 3. Tentukan Tujuan Evolusi
        if mode == "Manual":
            goal = f"INSTRUKSI WAJIB DARI OWNER: {user_instruction}"
            commit_msg = "Manual Update: Executed user instruction"
        else:
            # Ide acak untuk evolusi mandiri jika tidak ada instruksi
            ideas = [
                "Ubah skema warna menjadi dark mode elegan.",
                "Tambahkan elemen UI futuristik.",
                "Optimalkan tipografi agar lebih mudah dibaca.",
                "Tambahkan kutipan teknologi inspiratif di footer.",
                "Buat layout lebih asimetris namun rapi."
            ]
            goal = f"Evolusi Mandiri: {random.choice(ideas)}"
            commit_msg = "Auto Evolution: System upgrade"

        # 4. Kirim ke Gemini (The Architect)
        prompt = f"""
        Kamu adalah COS-X. Modifikasi kode HTML ini.
        DNA SAAT INI: {current_html}
        TUJUAN: {goal}
        SYARAT: 
        1. Output HANYA kode HTML valid (Single File). 
        2. Jangan sertakan markdown fence (```).
        3. Jangan hapus script 'log-entry' yang sudah ada, cukup modifikasi tampilannya jika perlu.
        4. Pastikan CSS tetap ada di dalam <style>.
        """
        
        new_html = get_gemini_response(prompt)
        
        # 5. Commit perubahan ke GitHub (Self-Writing)
        if "<html" in new_html:
            if sha_html:
                repo.update_file("templates/index.html", commit_msg, new_html, sha_html)
            else:
                repo.create_file("templates/index.html", commit_msg, new_html)

            # Jika mode manual selesai, reset instructions.txt
            if mode == "Manual" and sha_instr:
                repo.update_file("instructions.txt", "System: Done.", "Instruction executed.", sha_instr)

        return jsonify({"status": "Success", "mode": mode, "goal": goal})
    except Exception as e:
        return jsonify({"status": "Error", "detail": str(e)})

# Vercel butuh entry point ini
if __name__ == '__main__':
    app.run(debug=True)
