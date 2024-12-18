from fastapi import FastAPI
from .models import InputModel, OutputModel
from sklearn.cluster import AffinityPropagation
import os
model = AffinityPropagation(damping=int(os.environ['DAMPING']))

app = FastAPI()

@app.post(path="/route")
def predict(inp: InputModel) -> OutputModel:
    return OutputModel(output="hello world")
