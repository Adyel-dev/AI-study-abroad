# OpenRouter Integration Setup

## Overview
The application now uses **OpenRouter as the PRIMARY AI provider** with OpenAI as a fallback. This provides better cost-efficiency while maintaining reliability.

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# PRIMARY: OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free

# FALLBACK: OpenAI Configuration (required for embeddings)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Required Keys

**OpenRouter (Primary):**
- `OPENROUTER_API_KEY`: Your OpenRouter API key
  - Get it from: https://openrouter.ai/keys
- `OPENROUTER_MODEL`: Model to use (default: `meta-llama/llama-3.3-70b-instruct:free`)

**OpenAI (Fallback & Embeddings):**
- `OPENAI_API_KEY`: Your OpenAI API key (required for embeddings, used as fallback)
- `OPENAI_MODEL`: Fallback model (default: `gpt-4o-mini`)
- `OPENAI_EMBEDDING_MODEL`: Embedding model (default: `text-embedding-3-small`)

## How It Works

1. **Primary Provider (OpenRouter):**
   - All chat completions attempt to use OpenRouter first
   - Uses Llama 3.3 70B (free tier) by default
   - Faster and more cost-effective

2. **Fallback Provider (OpenAI):**
   - If OpenRouter fails or is unavailable, automatically falls back to OpenAI
   - Ensures reliability and continuity
   - Also used for embeddings (OpenRouter doesn't support embeddings)

3. **Automatic Failover:**
   - Seamless fallback if OpenRouter is down
   - Logs which provider was used for debugging
   - No user-facing errors during failover

## Services Updated

The following services now use the unified AI client:

- ✅ `services/counselor.py` - Main counselor service
- ✅ `services/counselor_query.py` - Search intent extraction
- ✅ `api/chat.py` - Simple Q&A chat
- ✅ `services/embeddings.py` - Still uses OpenAI (OpenRouter doesn't support embeddings)

## Model Details

### OpenRouter Primary Model
- **Model**: `meta-llama/llama-3.3-70b-instruct:free`
- **Provider**: Meta (via OpenRouter)
- **Features**: Free tier available, excellent instruction following
- **Best for**: General counseling conversations, question answering

### OpenAI Fallback Model
- **Model**: `gpt-4o-mini` (default)
- **Provider**: OpenAI
- **Features**: Reliable, well-tested
- **Best for**: Fallback when OpenRouter unavailable

## Getting OpenRouter API Key

1. Visit https://openrouter.ai/
2. Sign up or log in
3. Go to Keys section: https://openrouter.ai/keys
4. Create a new API key
5. Copy the key to your `.env` file

## Testing

After setup, test the integration:

1. Start the Flask application
2. Try the counselor chat
3. Check logs to see which provider was used:
   - Look for: `"AI response from openrouter using meta-llama/llama-3.3-70b-instruct:free"`
   - Or: `"AI response from openai using gpt-4o-mini"`

## Troubleshooting

### OpenRouter not working?
- Check your API key is correct
- Verify the model name is available: `meta-llama/llama-3.3-70b-instruct:free`
- Check OpenRouter status: https://openrouter.ai/status
- System will automatically fallback to OpenAI

### Both providers failing?
- Ensure at least one API key is set (`OPENROUTER_API_KEY` or `OPENAI_API_KEY`)
- Check network connectivity
- Verify API keys are valid

### Embeddings not working?
- Embeddings always use OpenAI (OpenRouter doesn't support them)
- Ensure `OPENAI_API_KEY` is set
- Check `OPENAI_EMBEDDING_MODEL` is correct

## Cost Optimization

**Using OpenRouter (Free Tier):**
- Llama 3.3 70B is available on free tier
- Significantly reduces AI costs
- Good performance for counseling tasks

**Fallback to OpenAI:**
- Only used if OpenRouter fails
- `gpt-4o-mini` is cost-effective
- Ensures reliability

## Code Example

```python
from services.ai_client import chat_completion

# This automatically tries OpenRouter first, then OpenAI
response = chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    temperature=0.7,
    max_tokens=500
)

print(response['content'])  # The AI response
print(response['provider'])  # 'openrouter' or 'openai'
print(response['model'])     # Model used
```

## Notes

- **Embeddings**: Still use OpenAI exclusively (OpenRouter doesn't support embeddings)
- **Logging**: Check logs to see which provider handled each request
- **Error Handling**: Automatic fallback ensures reliability
- **Model Updates**: You can change models in `.env` without code changes

