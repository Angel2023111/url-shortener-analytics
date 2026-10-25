from fastapi import FastAPI

# Create the FastAPI application.
app = FastAPI(
    title="URL Shortener API",
    description="A URL shortening and click analytics service.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Check whether the API is responding."""
    return {
        "status": "healthy",
        "service": "url-shortener"
    }
