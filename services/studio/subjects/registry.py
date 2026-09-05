"""Immutable exact-version lookup for Subject Capability contracts."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from services.studio.subjects.contracts import (
    ActivityActionContract,
    ActivityContract,
    ReducerContract,
    RendererContract,
    PayloadValidatorContract,
    SubjectCapabilityProfile,
    ValidatorContract,
    ValidationResult,
)


class SubjectCapabilityError(ValueError):
    """Raised when a persisted Studio capability reference cannot resolve exactly."""


class SubjectCapabilityRegistry:
    """A process-local immutable registry; request, user, and database data cannot mutate it."""

    def __init__(self, profiles: tuple[SubjectCapabilityProfile, ...]) -> None:
        profiles_by_key: dict[tuple[str, str], SubjectCapabilityProfile] = {}
        activities: dict[tuple[str, str, str, str], ActivityContract] = {}
        renderers: dict[tuple[str, str, str, str], RendererContract] = {}
        validators: dict[tuple[str, str, str, str], ValidatorContract] = {}
        payload_validators: dict[tuple[str, str, str, str], PayloadValidatorContract] = {}
        reducers: dict[tuple[str, str, str, str], ReducerContract] = {}
        actions: dict[tuple[str, str, str, str, str], ActivityActionContract] = {}
        for profile in profiles:
            self._register(profiles_by_key, (profile.subject_key, profile.profile_version), profile, "Subject profile")
            for renderer in profile.renderers:
                if renderer.subject_key != profile.subject_key:
                    raise SubjectCapabilityError("Renderer subject must match its profile.")
                self._register(
                    renderers,
                    (profile.subject_key, profile.profile_version, renderer.renderer_key, renderer.renderer_version),
                    renderer,
                    "Renderer contract",
                )
            for validator in profile.validators:
                self._register(
                    validators,
                    (profile.subject_key, profile.profile_version, validator.validator_key, validator.validator_version),
                    validator,
                    "Validator contract",
                )
            for payload_validator in profile.payload_validators:
                self._register(
                    payload_validators,
                    (
                        profile.subject_key, profile.profile_version,
                        payload_validator.payload_validator_key,
                        payload_validator.payload_schema_version,
                    ),
                    payload_validator,
                    "Payload validator contract",
                )
            for reducer in profile.reducers:
                self._register(
                    reducers,
                    (profile.subject_key, profile.profile_version, reducer.reducer_key, reducer.reducer_version),
                    reducer,
                    "Reducer contract",
                )
            for activity in profile.activities:
                self._validate_activity(profile, activity, renderers, validators, payload_validators, reducers)
                self._register(
                    activities,
                    (profile.subject_key, profile.profile_version, activity.activity_key, activity.activity_version),
                    activity,
                    "Activity contract",
                )
                for action in activity.actions:
                    self._register(
                        actions,
                        (
                            profile.subject_key, profile.profile_version,
                            activity.activity_key,
                            activity.activity_version,
                            action.action_key,
                        ),
                        action,
                        "Activity action contract",
                    )
        self._profiles = MappingProxyType(profiles_by_key)
        self._activities = MappingProxyType(activities)
        self._renderers = MappingProxyType(renderers)
        self._validators = MappingProxyType(validators)
        self._payload_validators = MappingProxyType(payload_validators)
        self._reducers = MappingProxyType(reducers)
        self._actions = MappingProxyType(actions)

    @staticmethod
    def _register(target: dict[object, object], key: object, value: object, label: str) -> None:
        if key in target:
            raise SubjectCapabilityError(f"Duplicate {label}: {key!r}.")
        target[key] = value

    @staticmethod
    def _validate_activity(
        profile: SubjectCapabilityProfile,
        activity: ActivityContract,
        renderers: Mapping[tuple[str, str, str, str], RendererContract],
        validators: Mapping[tuple[str, str, str, str], ValidatorContract],
        payload_validators: Mapping[tuple[str, str, str, str], PayloadValidatorContract],
        reducers: Mapping[tuple[str, str, str, str], ReducerContract],
    ) -> None:
        if activity.subject_key != profile.subject_key:
            raise SubjectCapabilityError("Activity subject must match its profile.")
        renderer = renderers.get((profile.subject_key, profile.profile_version, activity.renderer_key, activity.renderer_version))
        if renderer is None or activity.activity_key not in renderer.supported_activity_keys:
            raise SubjectCapabilityError("Activity renderer relation is not registered.")
        if (profile.subject_key, profile.profile_version, activity.reducer_key, activity.reducer_version) not in reducers:
            raise SubjectCapabilityError("Activity reducer is not registered.")
        if (
            profile.subject_key, profile.profile_version,
            activity.initial_scene_payload_validator_key,
            activity.initial_scene_payload_schema_version,
        ) not in payload_validators:
            raise SubjectCapabilityError("Activity initial scene payload validator is not registered.")
        for action in activity.actions:
            if not action.action_key or not action.event_kind:
                raise SubjectCapabilityError("Activity actions must have keys and event kinds.")
            if (profile.subject_key, profile.profile_version, action.payload_validator_key, action.payload_schema_version) not in payload_validators:
                raise SubjectCapabilityError("Activity action payload validator is not registered.")
            if action.action_key not in renderer.supported_action_keys:
                raise SubjectCapabilityError("Activity action is not supported by its Renderer.")
            if action.validator_key is not None and (
                profile.subject_key, profile.profile_version, action.validator_key, action.validator_version
            ) not in validators:
                raise SubjectCapabilityError("Activity action validator is not registered.")
        declared_validator_keys = {action.validator_key for action in activity.actions if action.validator_key is not None}
        if not set(renderer.required_validator_keys).issubset(declared_validator_keys):
            raise SubjectCapabilityError("Renderer required validators are not bound to Activity actions.")

    def resolve_profile(self, subject_key: str, profile_version: str) -> SubjectCapabilityProfile:
        return self._resolve(self._profiles, (subject_key, profile_version), "Subject profile")

    def activities_for_profile(self, subject_key: str, profile_version: str) -> tuple[ActivityContract, ...]:
        """Return exact-version Activity declarations without applying a latest policy."""

        return self.resolve_profile(subject_key, profile_version).activities

    def renderers_for_profile(self, subject_key: str, profile_version: str) -> tuple[RendererContract, ...]:
        """Return exact-version Renderer declarations without applying a latest policy."""

        return self.resolve_profile(subject_key, profile_version).renderers

    def resolve_activity(self, subject_key: str, profile_version: str, activity_key: str, activity_version: str) -> ActivityContract:
        return self._resolve(self._activities, (subject_key, profile_version, activity_key, activity_version), "Activity contract")

    def resolve_renderer(self, subject_key: str, profile_version: str, renderer_key: str, renderer_version: str) -> RendererContract:
        return self._resolve(self._renderers, (subject_key, profile_version, renderer_key, renderer_version), "Renderer contract")

    def resolve_action(
        self,
        subject_key: str,
        profile_version: str,
        activity_key: str,
        activity_version: str,
        action_key: str,
    ) -> ActivityActionContract:
        return self._resolve(
            self._actions,
            (subject_key, profile_version, activity_key, activity_version, action_key),
            "Activity action contract",
        )

    def resolve_reducer(self, subject_key: str, profile_version: str, reducer_key: str, reducer_version: str) -> ReducerContract:
        return self._resolve(self._reducers, (subject_key, profile_version, reducer_key, reducer_version), "Reducer contract")

    def validate_payload(
        self,
        subject_key: str,
        profile_version: str,
        payload_validator_key: str,
        payload_schema_version: str,
        payload: Mapping[str, object],
    ) -> None:
        contract = self._resolve(
            self._payload_validators,
            (subject_key, profile_version, payload_validator_key, payload_schema_version),
            "Payload validator contract",
        )
        try:
            contract.validator(payload)
        except (TypeError, ValueError) as error:
            raise SubjectCapabilityError("Payload violates its registered exact contract.") from error

    def validate_scene(
        self,
        *,
        subject_key: str,
        subject_profile_version: str,
        activity_key: str,
        activity_version: str,
        renderer_key: str,
        renderer_version: str,
        payload_schema_version: str,
        seed_payload: Mapping[str, object],
        locale: str,
        direction: str,
    ) -> ActivityContract:
        self.resolve_profile(subject_key, subject_profile_version)
        self.validate_locale(subject_key, locale=locale, direction=direction)
        activity = self.resolve_activity(subject_key, subject_profile_version, activity_key, activity_version)
        renderer = self.resolve_renderer(subject_key, subject_profile_version, renderer_key, renderer_version)
        if (
            activity.renderer_key != renderer.renderer_key
            or activity.renderer_version != renderer.renderer_version
            or activity_key not in renderer.supported_activity_keys
        ):
            raise SubjectCapabilityError("Activity and renderer are not an approved exact-version relation.")
        if payload_schema_version != activity.initial_scene_payload_schema_version:
            raise SubjectCapabilityError("Scene payload schema version is not supported by the Activity contract.")
        self.validate_payload(
            subject_key,
            subject_profile_version,
            activity.initial_scene_payload_validator_key,
            payload_schema_version,
            seed_payload,
        )
        return activity

    def validate_subject_event(
        self,
        *,
        subject_key: str,
        subject_profile_version: str,
        activity_key: str,
        activity_version: str,
        action_key: str,
        payload_schema_version: str,
        payload: Mapping[str, object],
        activity_state: Mapping[str, object] | None = None,
    ) -> tuple[ActivityActionContract, ValidationResult | None]:
        action = self.resolve_action(
            subject_key,
            subject_profile_version,
            activity_key,
            activity_version,
            action_key,
        )
        if action.payload_schema_version != payload_schema_version:
            raise SubjectCapabilityError("Subject event payload schema version is not supported by its action.")
        self.validate_payload(subject_key, subject_profile_version, action.payload_validator_key, payload_schema_version, payload)
        activity = self.resolve_activity(subject_key, subject_profile_version, activity_key, activity_version)
        self.resolve_reducer(subject_key, subject_profile_version, activity.reducer_key, activity.reducer_version)
        if action.validator_key is not None:
            validator = self._resolve(
                self._validators,
                (subject_key, subject_profile_version, action.validator_key, action.validator_version),
                "Validator contract",
            )
            if validator.requires_activity_state:
                if activity_state is None:
                    raise SubjectCapabilityError("Semantic validation requires the authoritative activity state.")
                validator_payload: Mapping[str, object] = {
                    "action": dict(payload),
                    "activity_state": dict(activity_state),
                }
            else:
                validator_payload = payload
            try:
                result = validator.validator(validator_payload)
            except (TypeError, ValueError) as error:
                raise SubjectCapabilityError("Semantic validation rejected the operation.") from error
            if not isinstance(result, ValidationResult):
                raise SubjectCapabilityError("Semantic validators must return the registered ValidationResult contract.")
            activity_action_keys = {registered.action_key for registered in activity.actions}
            if not set(result.next_action_keys).issubset(activity_action_keys):
                raise SubjectCapabilityError("Validation result next actions must be registered by the Activity contract.")
            return action, result
        return action, None

    def validate_locale(self, subject_key: str, *, locale: str, direction: str) -> tuple[str, str]:
        if not any(key[0] == subject_key for key in self._profiles):
            raise SubjectCapabilityError(f"Unknown subject: {subject_key!r}.")
        if not isinstance(locale, str) or not locale.strip() or len(locale) > 16:
            raise SubjectCapabilityError("Locale must be a bounded non-empty string.")
        if direction not in {"ltr", "rtl", "auto"}:
            raise SubjectCapabilityError("Direction must be ltr, rtl, or auto.")
        return locale, direction

    @staticmethod
    def _resolve(mapping: Mapping[object, object], key: object, label: str):
        try:
            return mapping[key]
        except KeyError as error:
            raise SubjectCapabilityError(f"Unsupported {label}: {key!r}.") from error
