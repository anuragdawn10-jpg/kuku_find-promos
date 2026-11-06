api_key = _config_value("GROQ_API_KEY")
model = model or _config_value("GROQ_MODEL", "llama-3.3-70b-versatile")
