"""Chat interaction and conversation management tools."""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


def generate_chat_response(
    user_message: str,
    context: Dict[str, Any],
    response_templates: Optional[Dict[str, str]] = None,
) -> str:
    """Generate appropriate chat response based on user message and context.
    
    Args:
        user_message: User's message
        context: Conversation context
        response_templates: Optional response templates
        
    Returns:
        Generated response
    """
    intent = extract_chat_intent(user_message)
    
    if response_templates and intent in response_templates:
        template = response_templates[intent]
        return template.format(**context)
    
    # Default responses based on intent
    responses = {
        "greeting": "Hello! How can I help you with your application today?",
        "application_status": f"Your application status is: {context.get('status', 'under review')}",
        "interview_scheduling": "I'd be happy to help you schedule an interview. What times work best for you?",
        "job_info": f"This position is for {context.get('job_title', 'a role')} at {context.get('company_name', 'our company')}",
        "salary_question": "Salary information will be discussed during the interview process.",
        "thanks": "You're welcome! Feel free to ask if you have any other questions.",
        "goodbye": "Thank you for your interest! We'll be in touch soon.",
        "unknown": "I'm not sure I understand. Could you please rephrase your question?",
    }
    
    return responses.get(intent, responses["unknown"])


def extract_chat_intent(message: str) -> str:
    """Extract intent from user message.
    
    Args:
        message: User's message
        
    Returns:
        Intent category
    """
    message_lower = message.lower()
    
    # Intent patterns
    patterns = {
        "greeting": r"\b(hello|hi|hey|good morning|good afternoon)\b",
        "application_status": r"\b(status|application|where|when|timeline)\b",
        "interview_scheduling": r"\b(interview|schedule|meeting|available|time)\b",
        "job_info": r"\b(job|role|position|responsibilities|requirements)\b",
        "salary_question": r"\b(salary|pay|compensation|benefits)\b",
        "thanks": r"\b(thank|thanks|appreciate)\b",
        "goodbye": r"\b(bye|goodbye|see you|later)\b",
    }
    
    for intent, pattern in patterns.items():
        if re.search(pattern, message_lower):
            return intent
    
    return "unknown"


def maintain_conversation_context(
    conversation_history: List[Dict[str, Any]],
    max_history: int = 10,
) -> Dict[str, Any]:
    """Maintain and summarize conversation context.
    
    Args:
        conversation_history: List of previous messages
        max_history: Maximum messages to keep in context
        
    Returns:
        Context dictionary
    """
    # Keep only recent messages
    recent_history = conversation_history[-max_history:] if len(conversation_history) > max_history else conversation_history
    
    # Extract key information
    topics_discussed = set()
    questions_asked = []
    
    for message in recent_history:
        if message.get("role") == "user":
            intent = extract_chat_intent(message.get("content", ""))
            topics_discussed.add(intent)
            if "?" in message.get("content", ""):
                questions_asked.append(message.get("content"))
    
    return {
        "message_count": len(recent_history),
        "topics_discussed": list(topics_discussed),
        "questions_asked": questions_asked,
        "last_user_message": recent_history[-1].get("content") if recent_history and recent_history[-1].get("role") == "user" else None,
        "conversation_summary": f"Discussed {len(topics_discussed)} topics over {len(recent_history)} messages",
    }


def handle_chat_errors(
    error: Exception,
    user_message: str,
    context: Dict[str, Any],
) -> str:
    """Handle chat errors gracefully.
    
    Args:
        error: Exception that occurred
        user_message: User's message that caused error
        context: Conversation context
        
    Returns:
        Error response message
    """
    logger.error(f"Chat error: {error} | User message: {user_message}")
    
    error_responses = {
        "ValueError": "I'm having trouble understanding your request. Could you please rephrase?",
        "KeyError": "I'm missing some information. Could you provide more details?",
        "TimeoutError": "I'm experiencing some delays. Please try again in a moment.",
        "ConnectionError": "I'm having connectivity issues. Please try again shortly.",
    }
    
    error_type = type(error).__name__
    return error_responses.get(error_type, "I encountered an issue. Please try again or contact support.")


def format_chat_message(
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Format chat message with metadata.
    
    Args:
        role: Role (user, assistant, system)
        content: Message content
        metadata: Optional additional metadata
        
    Returns:
        Formatted message dictionary
    """
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    }
    
    if metadata:
        message["metadata"] = metadata
    
    return message


def validate_chat_input(
    message: str,
    max_length: int = 1000,
    min_length: int = 1,
) -> tuple[bool, Optional[str]]:
    """Validate chat input.
    
    Args:
        message: User's message
        max_length: Maximum message length
        min_length: Minimum message length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not message or not message.strip():
        return False, "Message cannot be empty"
    
    if len(message) > max_length:
        return False, f"Message too long (max {max_length} characters)"
    
    if len(message) < min_length:
        return False, f"Message too short (min {min_length} character)"
    
    # Check for potentially malicious content
    dangerous_patterns = [
        r'<script[^>]*>',  # Script tags
        r'javascript:',     # JavaScript URLs
        r'on\w+\s*=',      # Event handlers
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return False, "Message contains invalid content"
    
    return True, None


def extract_questions_from_message(message: str) -> List[str]:
    """Extract questions from user message.
    
    Args:
        message: User's message
        
    Returns:
        List of questions found
    """
    # Split by sentence and identify questions
    sentences = re.split(r'[.!?]+', message)
    questions = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Check if it's a question (ends with ? or starts with question word)
        question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'is', 'are', 'can', 'could', 'would']
        
        if sentence.endswith('?') or any(sentence.lower().startswith(word) for word in question_words):
            questions.append(sentence)
    
    return questions


def generate_suggested_responses(
    user_message: str,
    context: Dict[str, Any],
) -> List[str]:
    """Generate suggested quick responses.
    
    Args:
        user_message: User's message
        context: Conversation context
        
    Returns:
        List of suggested responses
    """
    intent = extract_chat_intent(user_message)
    
    suggestions = {
        "greeting": [
            "I'd like to check my application status",
            "I have questions about the position",
            "I'd like to schedule an interview",
        ],
        "application_status": [
            "When can I expect to hear back?",
            "What are the next steps?",
            "Can I provide additional information?",
        ],
        "interview_scheduling": [
            "I'm available this week",
            "Can we do a phone interview first?",
            "What times work for your team?",
        ],
        "job_info": [
            "What are the main responsibilities?",
            "What skills are most important?",
            "Tell me about the team",
        ],
        "salary_question": [
            "What is the salary range?",
            "What benefits do you offer?",
            "Is the salary negotiable?",
        ],
    }
    
    return suggestions.get(intent, [
        "Can you tell me more?",
        "I have another question",
        "Thank you for the information",
    ])


def create_chat_session(
    candidate_id: str,
    session_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create new chat session.
    
    Args:
        candidate_id: ID of candidate
        session_type: Type of chat session
        metadata: Optional session metadata
        
    Returns:
        Chat session object
    """
    session = {
        "session_id": f"chat_{candidate_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "candidate_id": candidate_id,
        "session_type": session_type,
        "started_at": datetime.now().isoformat(),
        "status": "active",
        "message_count": 0,
        "messages": [],
    }
    
    if metadata:
        session["metadata"] = metadata
    
    return session


def close_chat_session(
    session: Dict[str, Any],
    reason: str = "completed",
) -> Dict[str, Any]:
    """Close chat session.
    
    Args:
        session: Chat session to close
        reason: Reason for closing
        
    Returns:
        Updated session object
    """
    session["status"] = "closed"
    session["closed_at"] = datetime.now().isoformat()
    session["close_reason"] = reason
    
    # Calculate session statistics
    if session.get("messages"):
        duration_minutes = len(session["messages"]) * 2  # Rough estimate
        session["duration_minutes"] = duration_minutes
        session["final_message_count"] = len(session["messages"])
    
    return session


def analyze_conversation_sentiment(
    messages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Analyze sentiment of conversation.
    
    Args:
        messages: List of conversation messages
        
    Returns:
        Sentiment analysis results
    """
    # Simple keyword-based sentiment (in production, would use NLP models)
    positive_keywords = ['great', 'excellent', 'good', 'happy', 'excited', 'thank', 'perfect']
    negative_keywords = ['bad', 'poor', 'disappointed', 'frustrated', 'confused', 'unhappy']
    
    positive_count = 0
    negative_count = 0
    
    for message in messages:
        if message.get("role") == "user":
            content_lower = message.get("content", "").lower()
            positive_count += sum(1 for kw in positive_keywords if kw in content_lower)
            negative_count += sum(1 for kw in negative_keywords if kw in content_lower)
    
    total = positive_count + negative_count
    if total == 0:
        sentiment = "neutral"
        score = 0.5
    else:
        score = positive_count / total
        if score > 0.6:
            sentiment = "positive"
        elif score < 0.4:
            sentiment = "negative"
        else:
            sentiment = "neutral"
    
    return {
        "sentiment": sentiment,
        "sentiment_score": round(score, 2),
        "positive_indicators": positive_count,
        "negative_indicators": negative_count,
    }
