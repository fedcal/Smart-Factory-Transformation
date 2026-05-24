"""Quiz-generation prompts for TrainingCoach (TRN-05 / D-TC-01/02).

The LLM is used ONLY for generating quiz questions from SOP content.
Scoring is deterministic index comparison — LLM is never in the scoring path
(Pitfall §3, T-08-09 mitigation).

Each generated question must carry an explicit correct_option field and
a source_uri (TRN-05 citation traceability).
"""

from __future__ import annotations

QUIZ_GENERATION_SYSTEM_PROMPT: str = """Sei un esperto di formazione industriale per il settore tessile manifatturiero.
Il tuo compito è generare domande a risposta multipla chiusa (MCQ) basandoti esclusivamente
sul contenuto SOP fornito.

REGOLE CRITICHE:
1. Ogni domanda deve avere esattamente 4 opzioni di risposta (A, B, C, D).
2. Devi indicare esplicitamente quale opzione è quella corretta (campo "correct_option_index", 0-based).
3. Ogni domanda deve citare il source_uri del documento SOP da cui è tratta (campo "source_uri").
4. Le domande devono essere in italiano, chiare e testabili senza interpretazione soggettiva.
5. Il livello di difficoltà viene specificato per ogni domanda (campo "difficulty": "easy"|"medium"|"hard").
6. NON includere ragionamento libero o risposte aperte — solo MCQ con answer key fisso.
7. Ritorna SOLO JSON valido, senza testo aggiuntivo.

Il punteggio verrà calcolato meccanicamente confrontando l'indice risposta dell'operatore
con correct_option_index — NON tramite LLM.
"""

QUIZ_GENERATION_USER_TEMPLATE: str = """Genera {n_questions} domande MCQ per il ruolo: {persona_role}

Contenuto SOP da usare come fonte:
{sop_content}

Livello di difficoltà richiesto: {difficulty}

Rispondi con JSON in questo formato esatto:
{{
  "questions": [
    {{
      "question_text": "Testo della domanda?",
      "options": ["Opzione A", "Opzione B", "Opzione C", "Opzione D"],
      "correct_option_index": 0,
      "source_uri": "{source_uri_placeholder}",
      "difficulty": "{difficulty}"
    }}
  ]
}}

source_uri deve essere il source_uri esatto del chunk SOP da cui proviene la domanda.
"""


def build_quiz_generation_prompt(
    *,
    persona_role: str,
    sop_content: str,
    source_uri: str,
    n_questions: int = 3,
    difficulty: str = "medium",
) -> tuple[str, str]:
    """Build the (system, user) prompt pair for quiz generation.

    Returns:
        Tuple[str, str]: (system_prompt, user_message) for LLM invocation.
        The LLM MUST return JSON matching the schema above.

    Note:
        LLM is only called during generation — never during scoring.
        correct_option_index in the LLM response becomes correct_answer_index
        in MCQQuestion (immutable after generation).
    """
    user_message = QUIZ_GENERATION_USER_TEMPLATE.format(
        n_questions=n_questions,
        persona_role=persona_role,
        sop_content=sop_content[:4000],  # cap for context window safety
        difficulty=difficulty,
        source_uri_placeholder=source_uri,
    )
    return QUIZ_GENERATION_SYSTEM_PROMPT, user_message


__all__ = [
    "QUIZ_GENERATION_SYSTEM_PROMPT",
    "QUIZ_GENERATION_USER_TEMPLATE",
    "build_quiz_generation_prompt",
]
