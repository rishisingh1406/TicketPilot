from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


"""
the request json should contain the user id and message 

the pydantic schema should validate 2 things the user id to be numeric and the user message to be string

in another layers or in another parts we will write our business logic here we will only do the implementation part 

user id should be numeric and user message should be string

"""