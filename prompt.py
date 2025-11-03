def prompt_texts(texts):
   data = f"""
Translate the following English transcript into natural, conversational Hindi. Keep the timing markers [00:00:00] etc. exactly as they are, and place the Hindi translation right after each marker on the same line. Maintain the original paragraph flow and spoken style (e.g., casual phrases like "cuz" → "kyunki").

script:
[{texts}]

"""
   return data