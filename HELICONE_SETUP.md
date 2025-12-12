# Helicone Setup Guide

Helicone is a proxy service that provides cost tracking, caching, and optimization for LLM APIs. It's **free for up to 100k requests/month**.

## Quick Setup (5 minutes)

### 1. Create Helicone Account
1. Go to https://helicone.ai
2. Sign up with your email or GitHub
3. Verify your email

### 2. Get API Key
1. Go to your Helicone dashboard
2. Navigate to "API Keys" section
3. Click "Create API Key"
4. Copy the key (starts with `sk-helicone-`)

### 3. Add to .env File
Add this line to your `.env` file:
```bash
HELICONE_API_KEY=sk-helicone-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. Test the Integration
Run the demo:
```bash
python examples/model_router_caching_demo.py
```

## What Helicone Provides

### ✅ Cost Tracking
- Automatic cost calculation per request
- Cost breakdown by model (GPT-3.5 vs GPT-4)
- Cost analysis by user role
- Budget monitoring and alerts

### ✅ Request Caching
- Intelligent response caching
- Configurable TTL (24 hours default)
- Cache hit rate tracking
- Significant cost savings on repeated queries

### ✅ Analytics Dashboard
- Real-time usage metrics
- Performance analytics
- Cost optimization insights
- Request latency tracking

### ✅ Rate Limiting & Security
- Built-in rate limiting
- Request logging and audit trails
- Error tracking and monitoring

## Alternative: Run Without Helicone

If you prefer not to use Helicone, the system will work with direct OpenAI API calls, but you'll miss out on:
- Automatic cost tracking
- Request caching
- Advanced analytics
- Cost optimization features

The demo will automatically detect if Helicone is configured and adapt accordingly.

## Pricing

- **Free Tier**: 100,000 requests/month
- **Pro Tier**: $20/month for 1M requests
- **Enterprise**: Custom pricing

For development and testing, the free tier is more than sufficient.

## Benefits for This Project

1. **Requirement 3.1**: Cost tracking per request and user role ✅
2. **Requirement 3.2**: Model routing optimization ✅  
3. **Requirement 3.4**: Cost optimization through caching ✅
4. **Requirement 3.6**: Cache effectiveness demonstration ✅

## Troubleshooting

### Common Issues:

1. **"Invalid API Key"**
   - Ensure your Helicone API key starts with `sk-helicone-`
   - Check that it's correctly set in your `.env` file

2. **"Connection Error"**
   - Verify your internet connection
   - Check if Helicone service is operational at https://status.helicone.ai

3. **"Rate Limit Exceeded"**
   - You've exceeded the free tier limit
   - Consider upgrading or wait for the limit to reset

### Getting Help:
- Helicone Documentation: https://docs.helicone.ai
- Helicone Discord: https://discord.gg/helicone
- GitHub Issues: https://github.com/Helicone/helicone

## Next Steps

Once Helicone is set up, you can:
1. Run the full demo with cost tracking
2. View detailed analytics in the Helicone dashboard
3. Monitor cache effectiveness and cost savings
4. Set up budget alerts and optimization rules