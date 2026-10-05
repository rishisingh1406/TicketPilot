PS C:\Users\codew\OneDrive\Desktop\my python scripts\Agentic AI\Agents\ticketpilot> tree -F
Folder PATH listing for volume Windows
Volume serial number is 32A5-368C
C:\USERS\CODEW\ONEDRIVE\DESKTOP\MY PYTHON SCRIPTS\AGENTIC AI\AGENTS\TICKETPILOT\-F
Invalid path - \USERS\CODEW\ONEDRIVE\DESKTOP\MY PYTHON SCRIPTS\AGENTIC AI\AGENTS\TICKETPILOT\-F
No subfolders exist 

PS C:\Users\codew\OneDrive\Desktop\my python scripts\Agentic AI\Agents\ticketpilot> tree /F
Folder PATH listing for volume Windows
Volume serial number is 32A5-368C
C:.
│   .dockerignore
│   .env
│   .env.example
│   .gitignore
│   alembic.ini
│   Caddyfile
│   database.py
│   docker-compose.yml
│   Dockerfile
│   Dockerfile.streamlit
│   groq_smoke.py
│   how 7ac8964docker-compose.yml
│   models.py
│   pytest.ini
│   requirements-streamlit.txt
│   requirements.txt
│   schemas.py
│   ticket.json
│   
├───.deepeval
├───.pytest_cache
│   │   .gitignore
│   │   CACHEDIR.TAG
│   │   README.md
│   │   
│   └───v
│       └───cache
│               lastfailed
│               nodeids
│               
├───alembic
│   │   env.py
│   │   README
│   │   script.py.mako
│   │   
│   ├───versions
│   │   │   3251ba6a5b22_add_embeddings_to_knowledge_chunks.py
│   │   │   3b886ca58548_create_initial_ticketpilot_tables.py
│   │   │   3cfee17bd3ff_add_knowledge_chunks.py
│   │   │   3f50ba346be1_add_review_required_ticket_status.py
│   │   │   46e8219f5d85_add_reviewer_identity_and_answer.py
│   │   │   5858a27753d5_update_reviewer_action_enum.py
│   │   │   6e57950fc57b_.py
│   │   │   bf0dd3917422_add_reviews_table.py
│   │   │   e4945e8ad0a7_add_escalated_to_support_ticket_status.py
│   │   │   
│   │   └───__pycache__
│   │           3251ba6a5b22_add_embeddings_to_knowledge_chunks.cpython-312.pyc
│   │           3b886ca58548_create_initial_ticketpilot_tables.cpython-312.pyc
│   │           3cfee17bd3ff_add_knowledge_chunks.cpython-312.pyc
│   │           3ead35536c9f_add_review_required_ticket_status.cpython-312.pyc
│   │           3f50ba346be1_add_review_required_ticket_status.cpython-312.pyc
│   │           46e8219f5d85_add_reviewer_identity_and_answer.cpython-312.pyc
│   │           497b0bdceb3d_update_reviewer_action_enum.cpython-312.pyc
│   │           5858a27753d5_update_reviewer_action_enum.cpython-312.pyc
│   │           6e57950fc57b_.cpython-312.pyc
│   │           bf0dd3917422_add_reviews_table.cpython-312.pyc
│   │           e4945e8ad0a7_add_escalated_to_support_ticket_status.cpython-312.pyc
│   │           
│   └───__pycache__
│           env.cpython-312.pyc
│           
├───app
│   │   agent.py
│   │   embeddings.py
│   │   knowledge_ingestion.py
│   │   llm.py
│   │   logging_config.py
│   │   main.py
│   │   retrieval.py
│   │   reviewer_ui.py
│   │   ticket_service.py
│   │   __init__.py
│   │   
│   ├───data
│   │       knowledge_base.json
│   │       
│   └───__pycache__
│           agent.cpython-312.pyc
│           embeddings.cpython-312.pyc
│           knowledge_ingestion.cpython-312.pyc
│           llm.cpython-312.pyc
│           logging_config.cpython-312.pyc
│           main.cpython-312.pyc
│           retrieval.cpython-312.pyc
│           reviewer_ui.cpython-312.pyc
│           ticket_service.cpython-312.pyc
│           __init__.cpython-312.pyc
│           
├───docs
│   │   architecture-notes.md
│   │   data-flow.md
│   │   evaluation_metrics.md
│   │   requirements.md
│   │   review-workflow.md
│   │   
│   └───adr
│           ADR-001-bounded-react-loop.md
│           ADR-002.md
│           ADR-003-semantic-retrieval-pgvector.md
│           
├───eval
│   │   baseline_results.json
│   │   citation_judge.py
│   │   evaluator.py
│   │   golden_set.json
│   │   llm_factory.py
│   │   metrics.py
│   │   run_all.py
│   │   run_one.py
│   │   schemas.py
│   │   
│   ├───baselines
│   │       baseline_v1.json
│   │       baseline_v2.json
│   │       
│   ├───promptfoo
│   │   │   promptfooconfig.yaml
│   │   │   provider.py
│   │   │   
│   │   └───__pycache__
│   │           provider.cpython-312.pyc
│   │           
│   ├───rubrics
│   │       citation_faithfulness_v1.md
│   │       
│   └───__pycache__
│           citation_judge.cpython-312.pyc
│           evaluator.cpython-312.pyc
│           llm_factory.cpython-312.pyc
│           metrics.cpython-312.pyc
│           run_all.cpython-312.pyc
│           run_one.cpython-312.pyc
│           schemas.cpython-312.pyc
│           
├───scripts
│   │   seed_knowledge.py
│   │   
│   └───__pycache__
│           seed_knowledge.cpython-312.pyc
│           seed_knowledge.py
│           
├───tests
│   │   conftest.py
│   │   test_agent.py
│   │   test_api.py
│   │   test_citation_judge.py
│   │   test_embeddings_db.py
│   │   test_real_retrieval.py
│   │   test_retrieval.py
│   │   test_reviewer_ui.py
│   │   test_reviewer_workflow.py
│   │   test_ticket_service.py
│   │   test_ticket_service_integration.py
│   │   
│   └───__pycache__
│           conftest.cpython-312-pytest-9.1.1.pyc
│           test_agent.cpython-312-pytest-9.1.1.pyc
│           test_api.cpython-312-pytest-9.1.1.pyc
│           test_citation_judge.cpython-312-pytest-9.1.1.pyc
│           test_embeddings_db.cpython-312-pytest-9.1.1.pyc
│           test_real_retrieval.cpython-312-pytest-9.1.1.pyc
│           test_retrieval.cpython-312-pytest-9.1.1.pyc
│           test_reviewer_ui.cpython-312-pytest-9.1.1.pyc
│           test_reviewer_workflow.cpython-312-pytest-9.1.1.pyc
│           test_ticket_service.cpython-312-pytest-9.1.1.pyc
│           test_ticket_service_integration.cpython-312-pytest-9.1.1.pyc
│           
└───__pycache__
        database.cpython-312.pyc
        groq_smoke_test.cpython-312-pytest-9.1.1.pyc
        models.cpython-312.pyc
        schemas.cpython-312.pyc
        test_groq.cpython-312-pytest-9.1.1.pyc
        
PS C:\Users\codew\OneDrive\Desktop\my python scripts\Agentic AI\Agents\ticketpilot> 