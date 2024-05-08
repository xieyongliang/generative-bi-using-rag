from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from api.exception_handler import biz_exception
from api.main import router
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title='GenBI')


app = FastAPI(title='GenBI')

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # 允许所有源访问，可以根据需求进行修改
    allow_credentials=True,  # 允许发送凭据（如Cookie）
    allow_methods=['*'],  # 允许所有HTTP方法
    allow_headers=['*'],  # 允许所有请求头
)

# Global exception capture
biz_exception(app)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

@app.get("/", status_code=status.HTTP_302_FOUND)
def index():
    return RedirectResponse("static/WebSocket.html")