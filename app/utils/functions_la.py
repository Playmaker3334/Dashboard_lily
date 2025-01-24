import re

def extract_key_questions_answers(text_content):
    """
    Extracts key questions and answers (1, 3, 5) from the text content.
    Also extracts the final score obtained and the maximum score.
    """
    # Use regular expressions to find all questions and answers
    question_pattern = r'<p class="question">(.*?)<\/p>'
    answer_pattern = r'<p class="answer">(.*?)<\/p>'

    questions = re.findall(question_pattern, text_content, re.DOTALL)
    answers = re.findall(answer_pattern, text_content, re.DOTALL)

    # Define the indices of the key questions (1, 3, and 5)
    key_indices = [0, 2, 4]  # Corresponds to questions 1, 3, and 5

    extracted_data = {}

    for i in key_indices:
        if i < len(questions) and i < len(answers):
            question_text = re.sub('<.*?>', '', questions[i]).strip()  # Remove HTML tags
            answer_text = re.sub('<.*?>', '', answers[i]).strip()  # Remove HTML tags

            # Rename columns as requested
            if i == 0:
                extracted_data['veredicto_compra'] = question_text
                extracted_data['veredicto_compra_resultado'] = answer_text
            elif i == 2:
                extracted_data['min_puntos_compra'] = question_text
                extracted_data['min_puntos_compra_resultado'] = answer_text
            elif i == 4:
                # Extract final score obtained and maximum score
                puntaje_match = re.match(r'(\d+) pts / (\d+) pts', answer_text)
                if puntaje_match:
                    extracted_data['puntaje_final_obtenido'] = int(puntaje_match.group(1))
                    extracted_data['max_puntaje'] = int(puntaje_match.group(2))

    return extracted_data
