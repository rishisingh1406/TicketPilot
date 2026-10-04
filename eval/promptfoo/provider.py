import json

from eval.llm_factory import create_llm
from app.ticket_service import SYSTEM_PROMPT


llm = create_llm()


def call_api(prompt, options, context):
    response = llm.generate(
        [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )

    return {
        "output": json.dumps(
            response.model_dump(),
            ensure_ascii=False,
        )
    }