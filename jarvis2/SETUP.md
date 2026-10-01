# Jarvis 2 - Setup & Deployment Guide

## Prerequisites

- Docker & Docker Compose (recommended)
- OR Node.js 18+ & Python 3.11+
- PostgreSQL 15+ (if not using Docker)

## Local Development (Docker)

### Start Everything

```bash
cd jarvis-2
docker-compose up --build
```

Services:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/docs
- **Database:** PostgreSQL on localhost:5432

### Test API

```bash
# Health check
curl http://localhost:8000/health

# Get portfolio
curl http://localhost:8000/portfolio

# Ingest market data
curl -X POST http://localhost:8000/market-data \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "symbol=NIFTY&open_price=23500&high=23600&low=23400&close=23550&volume=50000000"

# Get agent analysis
curl http://localhost:8000/learning/analysis/STOCKS

# Get performance summary
curl http://localhost:8000/learning/performance

# Get improvement plan
curl http://localhost:8000/learning/improvement-plan/STOCKS
```

## Local Development (Manual)

### Backend

```bash
cd backend

# Create virtual env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL (Docker)
docker run -d -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16

# Run migrations
# (automatic on app start)

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

## Railway Deployment

### 1. Create Railway Services

```bash
# Login to Railway
railway login

# Create project
railway init

# Backend service
cd backend
railway add

# Frontend service
cd ../frontend
railway add

# Database
# Use Railway UI to add PostgreSQL plugin
```

### 2. Configure Environment Variables

Backend:
```
DATABASE_URL=postgresql://user:password@host:port/jarvis2
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
SECRET_KEY=<generate-random-key>
```

Frontend:
```
VITE_API_URL=https://backend-url.railway.app
```

### 3. Deploy

```bash
# Push to Railway
railway up

# Or use GitHub auto-deploy:
# 1. Push code to GitHub
# 2. Connect repository in Railway UI
# 3. Auto-deploy on push
```

### 4. Verify Deployment

```bash
# Check backend health
curl https://backend-url.railway.app/health

# Check frontend
open https://frontend-url.railway.app
```

## Database Migrations

### Initial Setup

Migrations run automatically on app start. To manually create tables:

```bash
# In Python shell or script:
from database import engine, Base
Base.metadata.create_all(bind=engine)
```

## Learning System Testing

### Daily Analysis

```bash
# Analyze STOCKS agent performance
curl http://localhost:8000/learning/analysis/STOCKS

# Response includes:
# - Win rate, avg win/loss
# - Confidence score (0-1)
# - Market conditions
# - Strategy adjustment suggestions
```

### Strategy Optimization

```bash
# Get optimized parameters for current market
curl http://localhost:8000/learning/strategy/STOCKS

# Response includes:
# - Entry thresholds
# - Exit thresholds
# - Stop loss & take profit levels
```

### Performance Tracking

```bash
# Get all agents' performance (track toward 90%)
curl http://localhost:8000/learning/performance

# Response includes per-agent:
# - Total trades
# - Win rate
# - Status (EXCELLENT/STRONG/GOOD/FAIR/POOR)
# - Recommended actions
```

### Improvement Plans

```bash
# Get auto-generated improvement steps
curl http://localhost:8000/learning/improvement-plan/STOCKS

# Response includes:
# - Priority-ranked improvement steps
# - Market opportunities
# - Backtest recommendations
```

## Monitoring

### Check Logs

```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f frontend

# Or direct server
tail -f /var/log/jarvis-2/backend.log
```

### Performance Dashboard

Access http://localhost:3000 to see:
- Live portfolio P&L
- Agent performance heatmap
- Real-time trade execution
- Daily win rates per agent
- Improvement recommendations

## Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL
docker ps | grep postgres

# Or start PostgreSQL
docker-compose up db -d
```

### Frontend Can't Reach Backend
```bash
# Check CORS settings in backend
# Update frontend .env:
VITE_API_URL=http://localhost:8000
```

### Port Already in Use
```bash
# Change ports in docker-compose.yml:
ports:
  - "3001:3000"  # frontend
  - "8001:8000"  # backend
```

## Next Steps

1. Start the platform
2. Ingest market data via API or manual testing
3. Monitor agent performance dashboard
4. Review daily learning analysis
5. Implement improvement recommendations
6. Iterate until 90%+ win rate achieved

## Support

- API Docs: http://localhost:8000/docs
- README: See README.md for architecture details
- Issues: Check logs and health endpoints
