"""
Core API view handlers
"""

# pylint: disable=too-many-arguments

# stdlib
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, List, Tuple

# library
import yaml
from dicttoxml import dicttoxml as fxml
from quart import Quart, Response, jsonify, request
from quart_openapi import Resource
from voluptuous import Invalid, MultipleInvalid

# module
from avwx_api_core import validate
from avwx_api_core.token import Token, TokenManager


class BaseView(Resource):
    """Base API Endpoint"""

    note: str = None

    # Replace the key's name in the final response
    _key_repl: dict = None
    # Remove the following keys from the final response
    _key_remv: List[str] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._key_repl is None:
            self._key_repl = {}
        if self._key_remv is None:
            self._key_remv = []

    def format_dict(self, output: dict) -> dict:
        """Formats a dict by recursively replacing and removing key

        Returns the item as-is if not a dict
        """
        if not isinstance(output, dict):
            return output
        resp = {}
        for key, val in output.items():
            if key in self._key_remv:
                continue
            if key in self._key_repl:
                key = self._key_repl[key]
            if isinstance(val, dict):
                val = self.format_dict(val)
            elif isinstance(val, list):
                val = [self.format_dict(item) for item in val]
            resp[key] = val
        return resp

    def make_response(
        self,
        output: dict,
        # pylint: disable=redefined-builtin
        format: str = "json",
        code: int = 200,
        meta: str = "meta",
        root: str = "AVWX",
    ) -> Response:
        """Returns the output string based on format param"""
        output = self.format_dict(output)
        if "error" in output and meta not in output:
            output["timestamp"] = datetime.now(tz=timezone.utc)
        if self.note and isinstance(output, dict):
            if meta not in output:
                output[meta] = {}
            output[meta]["note"] = self.note
        if format == "xml":
            resp = Response(fxml(output, custom_root=root.upper()), mimetype="text/xml")
        elif format == "yaml":
            resp = Response(
                yaml.dump(output, default_flow_style=False), mimetype="text/x-yaml"
            )
        else:
            resp = jsonify(output)
        resp.status_code = code
        resp.headers["X-Robots-Tag"] = "noindex"
        return resp


def make_token_check(app: Quart) -> Callable:
    """Pass the core app to allow access to the token manager"""

    def token_check(func: Callable) -> Callable:
        """Checks token presense and validity for the endpoint"""

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            code, token = await self.validate_token(app.token)
            if code != 200:
                # If given a Param object
                for item in args:
                    if hasattr(item, "report_type"):
                        report_type = item.report_type
                        break
                # Other pulled from url or class default
                else:
                    report_type = kwargs.get("report_type", self.report_type)
                data = self.make_example_response(code, report_type, token)
                return self.make_response(data, code=code)
            if self.include_token:
                kwargs["token"] = token
            return await func(self, *args, **kwargs)

        return wrapper

    return token_check


VALIDATION_ERROR_MESSAGES = {
    401: 'You are missing the "Authorization" header or "token" parameter',
    403: "Your auth token is not allowed to access this resource",
    429: "Your auth token has hit it's daily rate limit. Considder upgrading your plan",
}


class AuthView(BaseView):
    """Views requiring token authentication"""

    # Filename of the sample response when token validation fails
    example: str = None

    # Whitelist of token plan types to access this endpoint
    # If None, all tokens are allowed
    plan_types: Tuple[str] = None

    # If True, add "token: Token" to route kwargs
    include_token: bool = False

    async def validate_token(self, token_manager: TokenManager) -> Tuple[int, Token]:
        """Validates thats an authorization token exists and is active

        Returns the response code and Token object
        """
        if not token_manager.active:
            return 200, None
        auth_token = request.headers.get("Authorization") or request.args.get("token")
        try:
            auth_token = validate.Token(auth_token)
        except (Invalid, MultipleInvalid):
            return 401, None
        auth_token = await token_manager.get(auth_token)
        if auth_token is None or not auth_token.active:
            return 403, auth_token
        if self.plan_types and not auth_token.is_developer:
            if not auth_token.valid_type(self.plan_types):
                return 403, auth_token
        # Increment returns False if rate limit exceeded
        if auth_token and not await token_manager.increment(auth_token):
            return 429, auth_token
        return 200, auth_token

    # pylint: disable=unused-argument,no-self-use
    def get_example_file(self, report_type: str) -> dict:
        """Load the example payload for the endpoint"""
        return {}

    def make_example_response(
        self, error_code: int, report_type: str, token: Token
    ) -> dict:
        """Returns an example payload when validation fails"""
        data = self.get_example_file(report_type)
        msg = VALIDATION_ERROR_MESSAGES[error_code]
        # Special handling for 403 errors
        if error_code == 403:
            if token is None:
                msg += "could not be found"
            elif not token.active:
                msg += "is inactive"
            elif not token.valid_type(self.plan_types):
                msg += f"plan ({token.type}) does not have permission to access this resource"
                msg += f". Requires a plan of type: {'/'.join(self.plan_types or [])}"
        if data:
            msg += ". Here's an example response for testing purposes"
        if isinstance(data, dict):
            data["meta"] = {"validation_error": msg}
        elif isinstance(data, list):
            data.insert(0, {"validation_error": msg})  # pylint: disable=no-member
        return data
