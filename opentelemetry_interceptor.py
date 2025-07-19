from __future__ import annotations

from typing import Any, Mapping, Protocol, Type
from contextlib import contextmanager

from temporalio import activity, api, client, converter, worker, workflow

with workflow.unsafe.imports_passed_through():
    from opentelemetry.propagate import inject, extract
    from opentelemetry import context as otel_context

# Header key for OpenTelemetry context
OTEL_CONTEXT_KEY = "otel-context"


class _InputWithHeaders(Protocol):
    headers: Mapping[str, api.common.v1.Payload]


def set_otel_header_from_context(
    input: _InputWithHeaders, payload_converter: converter.PayloadConverter
) -> None:
    """Inject OpenTelemetry context into Temporal headers."""
    otel_headers = {}
    inject(otel_headers)
    if otel_headers:
        input.headers = {
            **input.headers,
            OTEL_CONTEXT_KEY: payload_converter.to_payload(otel_headers),
        }


@contextmanager
def otel_context_from_header(
    input: _InputWithHeaders, payload_converter: converter.PayloadConverter
):
    """Extract and set OpenTelemetry context from Temporal headers."""
    otel_payload = input.headers.get(OTEL_CONTEXT_KEY)
    parent_context = otel_context.get_current()
    
    if otel_payload:
        otel_headers = payload_converter.from_payload(otel_payload, dict)
        parent_context = extract(otel_headers)
    
    # Set OpenTelemetry context using token
    token = otel_context.attach(parent_context)
    try:
        yield
    finally:
        otel_context.detach(token)


class OpenTelemetryContextPropagationInterceptor(client.Interceptor, worker.Interceptor):
    """Interceptor that propagates OpenTelemetry context through Temporal workflows."""

    def __init__(
        self,
        payload_converter: converter.PayloadConverter = converter.default().payload_converter,
    ) -> None:
        self._payload_converter = payload_converter

    def intercept_client(
        self, next: client.OutboundInterceptor
    ) -> client.OutboundInterceptor:
        return _OpenTelemetryContextPropagationClientOutboundInterceptor(
            next, self._payload_converter
        )

    def intercept_activity(
        self, next: worker.ActivityInboundInterceptor
    ) -> worker.ActivityInboundInterceptor:
        return _OpenTelemetryContextPropagationActivityInboundInterceptor(next)

    def workflow_interceptor_class(
        self, input: worker.WorkflowInterceptorClassInput
    ) -> Type[_OpenTelemetryContextPropagationWorkflowInboundInterceptor]:
        return _OpenTelemetryContextPropagationWorkflowInboundInterceptor


class _OpenTelemetryContextPropagationClientOutboundInterceptor(client.OutboundInterceptor):
    def __init__(
        self,
        next: client.OutboundInterceptor,
        payload_converter: converter.PayloadConverter,
    ) -> None:
        super().__init__(next)
        self._payload_converter = payload_converter

    async def start_workflow(
        self, input: client.StartWorkflowInput
    ) -> client.WorkflowHandle[Any, Any]:
        set_otel_header_from_context(input, self._payload_converter)
        return await super().start_workflow(input)


class _OpenTelemetryContextPropagationActivityInboundInterceptor(
    worker.ActivityInboundInterceptor
):
    async def execute_activity(self, input: worker.ExecuteActivityInput) -> Any:
        with otel_context_from_header(input, activity.payload_converter()):
            return await self.next.execute_activity(input)


class _OpenTelemetryContextPropagationWorkflowInboundInterceptor(
    worker.WorkflowInboundInterceptor
):
    def init(self, outbound: worker.WorkflowOutboundInterceptor) -> None:
        self.next.init(
            _OpenTelemetryContextPropagationWorkflowOutboundInterceptor(outbound)
        )

    async def execute_workflow(self, input: worker.ExecuteWorkflowInput) -> Any:
        with otel_context_from_header(input, workflow.payload_converter()):
            return await self.next.execute_workflow(input)


class _OpenTelemetryContextPropagationWorkflowOutboundInterceptor(
    worker.WorkflowOutboundInterceptor
):
    def start_activity(
        self, input: worker.StartActivityInput
    ) -> workflow.ActivityHandle:
        set_otel_header_from_context(input, workflow.payload_converter())
        return self.next.start_activity(input)

    async def start_child_workflow(
        self, input: worker.StartChildWorkflowInput
    ) -> workflow.ChildWorkflowHandle:
        set_otel_header_from_context(input, workflow.payload_converter())
        return await self.next.start_child_workflow(input)