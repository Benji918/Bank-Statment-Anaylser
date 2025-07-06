# AI Bank Statement Analyzer

An intelligent bank statement analysis tool that leverages artificial intelligence to automatically process, categorize, and analyze financial transactions from bank statements. This application provides insights into spending patterns, transaction categorization, and financial analytics.

## ERD diagram

![](https://github.com/Benji918/Bank-Statment-Anaylser/blob/dev/Untitled.png)

## Features

- **Automated Transaction Processing**: Upload and process bank statements in various formats
- **AI-Powered Categorization**: Intelligent categorization of transactions using machine learning
- **Financial Analytics**: Generate comprehensive reports and insights from transaction data
- **Asynchronous Processing**: Background task processing using Celery for handling large datasets
- **Real-time Monitoring**: Built-in task monitoring with Celery Flower
- **RESTful API**: Clean API endpoints for integration with other applications
- **Data Visualization**: Interactive charts and graphs for financial insights

## Technology Stack

- **Backend**: Python with Flask/FastAPI
- **Task Queue**: Celery with Redis/RabbitMQ
- **AI/ML**: Machine learning models for transaction analysis and categorization
- **Database**: PostgreSQL/SQLite for data persistence
- **Monitoring**: Celery Flower for task monitoring
- **Containerization**: Docker support (optional)

## Prerequisites

- Python 3.8+
- Redis or RabbitMQ (for Celery message broker)
- PostgreSQL (if using PostgreSQL as database)

## Installation

### Local Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AI-bank-statement-analyzer
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

5. **Initialize database**
   ```bash
   alembic upgrade head
   ```
    if a change is made to the DB then run this command to perform the migration(s)
    ```bash
   alembic revision --autogenerate -m "migration_name"
   alembic upgrade head
   ```
   


### Docker Setup (Optional)

You can also run the application using Docker for easier deployment and development:

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Or build individual containers**
   ```bash
   docker build -t ai-bank-analyzer .
   docker run -p 5000:5000 ai-bank-analyzer
   ```

## Running the Application

### 1. Start the Message Broker
Ensure Redis or RabbitMQ is running on your system.

For Redis:
```bash
redis-server
```

### 2. Start the Celery Worker
```bash
celery -A app.tasks.celery_app worker -l info
```

### 3. Start Celery Flower (Optional - for monitoring)
```bash
celery -A app.tasks.celery_app flower --port=5555
```

### 4. Start the Main Application
```bash
python app.py
```

The application will be available at:
- **Main Application**: http://localhost:8000
- **Celery Flower Dashboard**: http://localhost:5555

## API Endpoints

### Upload Bank Statement
```
POST /api/upload
Content-Type: multipart/form-data
```

### Get Analysis Results
```
GET /api/analysis/{analysis_id}
```

### Get Transaction Categories
```
GET /api/categories
```

### Get Financial Summary
```
GET /api/summary/{period}
```

## Usage

1. **Upload Bank Statement**: Use the web interface or API to upload your bank statement (PDF, CSV, or Excel format)

2. **Processing**: The system will automatically:
   - Extract transaction data
   - Clean and normalize the data
   - Apply AI models for categorization
   - Generate insights and analytics

3. **View Results**: Access your analysis through:
   - Web dashboard for visual insights
   - API endpoints for programmatic access
   - Export options for further analysis

## Configuration

Key configuration options in your `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI Models
OPENAI_API_KEY=your_openai_key_here

# Application
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
```

## Monitoring

### Celery Flower Dashboard
Access the Celery Flower dashboard at http://localhost:5555 to monitor:
- Active tasks
- Task history
- Worker status
- Task execution times
- Failed tasks and error logs

### Application Logs
Monitor application logs for debugging and performance tracking:
```bash
tail -f logs/app.log
```

## Supported File Formats

- **PDF**: Bank statements in PDF format
- **CSV**: Comma-separated transaction files
- **Excel**: .xlsx and .xls files


## AI Features

- **Transaction Categorization**: Automatic categorization into predefined categories (Food, Transportation, Entertainment, etc.)
- **Merchant Recognition**: Intelligent merchant name normalization
- **Spending Pattern Analysis**: Identification of spending trends and patterns
- **Anomaly Detection**: Detection of unusual transactions
- **Budget Recommendations**: AI-powered budget suggestions based on spending history

## Troubleshooting

### Common Issues

1. **Celery Worker Not Starting**
   - Ensure message broker (Redis/RabbitMQ) is running
   - Check celery configuration in settings

2. **File Upload Errors**
   - Verify file format is supported
   - Check file size limits
   - Ensure proper permissions

3. **Database Connection Issues**
   - Verify database credentials
   - Ensure database server is running
   - Check network connectivity

### Debug Mode
Run the application in debug mode for detailed error messages:
```bash
export FLASK_ENV=development
python app.py
```

## Performance Optimization

- **Batch Processing**: Large files are processed in chunks
- **Caching**: Redis caching for frequently accessed data
- **Database Indexing**: Optimized database queries
- **Async Processing**: Background processing for time-intensive tasks


