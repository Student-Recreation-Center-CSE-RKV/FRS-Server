class ExceptionHandler:
    def __init__(self, func, default_value=None, log_errors=True):
        """
        Wrapper class to handle exceptions in functions.
        
        :param func: The function to wrap
        :param default_value: The value to return in case of an exception
        :param log_errors: Whether to log the errors or not
        """
        self.func = func
        self.default_value = default_value
        self.log_errors = log_errors

    def __call__(self, *args, **kwargs):
        """
        Call the wrapped function with exception handling.
        """
        try:
            # Call the function with its arguments
            return self.func(*args, **kwargs)
        except Exception as e:
            # Handle the exception (log or print the error)
            if self.log_errors:
                print(f"Error in function '{self.func.__name__}': {e}")

            # Return a default value in case of an exception
            return self.default_value
