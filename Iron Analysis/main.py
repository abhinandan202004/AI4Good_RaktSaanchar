from fastapi import FastAPI

from routes.iron_overload import router


app = FastAPI(
    title="Iron Overload AI"
)

app.include_router(
    router
)
