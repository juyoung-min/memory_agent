# client 

### llm (v1/completions)
uv run client-model.py \
--model-name "EXAONE-3.5-2.4B-Instruct" \
--apipath /v1/completions \
--payload '{"model": "EXAONE-3.5-2.4B-Instruct", "prompt": "서울의 인구는 몇 명이야?", "max_tokens": 512}'


### llm (v1/chat/completions)
uv run client-model.py \
--apipath /v1/chat/completions \
--payload '{"model_name": "EXAONE-3.5-2.4B-Instruct", "messages": [{"role": "user", "content": "서울의 인구는 몇 명이야?"}], "max_tokens": 512}'

### embedding
uv run client-model.py \
--model-name "bge-m3" \
--apipath /v1/embeddings \
--payload '{"model": "bge-m3", "input": "이 문장을 벡터로 변환합니다."}'

### tts 
uv run client-model.py \
  --model-name tts \
  --apipath v2/models/tts/infer \
  --payload '{"inputs": [{"name": "text", "datatype": "BYTES", "shape": [1, 1], "data": [["안녕하세요. AI 어시스턴트입니다."]]}, {"name": "voice_name", "datatype": "BYTES", "shape": [1, 1], "data": [["sample_female"]]}], "outputs": [{"name": "waveform"}]}'

### stt