Module madsci.common.types.error_types
======================================
Service communication error types for MADSci.

Provides a hierarchy of exceptions for service-related errors,
enabling consistent error handling across CLI commands and client code.

Classes
-------

`MadsciServiceError(service_name: str, service_url: str, message: str)`
:   Base exception for service communication errors.
    
    All service-related exceptions inherit from this class, making it
    easy to catch any service error with a single ``except`` clause.
    
    Attributes:
        service_name: Human-readable name of the target service.
        service_url: URL that was being contacted.
    
    Initialise with service identification and a human-readable message.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

    ### Descendants

    * madsci.common.types.error_types.ServiceResponseError
    * madsci.common.types.error_types.ServiceTimeoutError
    * madsci.common.types.error_types.ServiceUnavailableError

`ServiceResponseError(service_name: str, service_url: str, message: str, status_code: int, response_body: str | None = None)`
:   Service returned an error HTTP response.
    
    Attributes:
        status_code: HTTP status code from the response.
        response_body: Raw response body text, if available.
    
    Initialise with the HTTP status code and optional response body.

    ### Ancestors (in MRO)

    * madsci.common.types.error_types.MadsciServiceError
    * builtins.Exception
    * builtins.BaseException

`ServiceTimeoutError(service_name: str, service_url: str, message: str)`
:   Service did not respond within the configured timeout.
    
    Initialise with service identification and a human-readable message.

    ### Ancestors (in MRO)

    * madsci.common.types.error_types.MadsciServiceError
    * builtins.Exception
    * builtins.BaseException

`ServiceUnavailableError(service_name: str, service_url: str, message: str)`
:   Service could not be reached (connection refused, DNS failure, etc.).
    
    Initialise with service identification and a human-readable message.

    ### Ancestors (in MRO)

    * madsci.common.types.error_types.MadsciServiceError
    * builtins.Exception
    * builtins.BaseException