from fastapi import FastAPI
app = FastAPI()

# the default route; which used in the health check
@app.get("/")
def welcome():
    return{
        "messege":"server is running"
    }