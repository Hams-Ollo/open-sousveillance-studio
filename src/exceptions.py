"""Custom exceptions for Open Sousveillance Studio.

All custom exceptions should be defined here to maintain consistency
and enable proper error handling across the application.
"""


class OpenSousveillanceError(Exception):
    """Base exception for all Open Sousveillance Studio errors."""

    pass


class ConfigurationError(OpenSousveillanceError):
    """Raised when configuration is invalid or missing."""

    pass


class ScrapingError(OpenSousveillanceError):
    """Raised when web scraping fails."""

    def __init__(self, message: str, url: str = None, status_code: int = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class DocumentProcessingError(OpenSousveillanceError):
    """Raised when document parsing fails (PDF, DOCX, etc.)."""

    def __init__(self, message: str, document_path: str = None):
        super().__init__(message)
        self.document_path = document_path


class AgentError(OpenSousveillanceError):
    """Raised when an agent fails to execute."""

    def __init__(self, message: str, agent_id: str = None, input_data: dict = None):
        super().__init__(message)
        self.agent_id = agent_id
        self.input_data = input_data


class LLMError(OpenSousveillanceError):
    """Raised when LLM API call fails."""

    def __init__(self, message: str, model: str = None, prompt_tokens: int = None):
        super().__init__(message)
        self.model = model
        self.prompt_tokens = prompt_tokens


class DatabaseError(OpenSousveillanceError):
    """Raised when database operations fail."""

    pass


class ValidationError(OpenSousveillanceError):
    """Raised when data validation fails."""

    def __init__(self, message: str, field: str = None, value: any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class ApprovalError(OpenSousveillanceError):
    """Raised when approval workflow fails."""

    def __init__(self, message: str, approval_id: str = None, status: str = None):
        super().__init__(message)
        self.approval_id = approval_id
        self.status = status


class RateLimitError(OpenSousveillanceError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class TimeoutError(OpenSousveillanceError):
    """Raised when an operation times out."""

    def __init__(self, message: str, timeout_seconds: int = None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
