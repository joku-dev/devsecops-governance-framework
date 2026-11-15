"""Explicit raw-native versus normalized event data for result index consumers."""
RESULT_EVENT_PROFILES = ('legacy-v1', 'portable-v1')
CONTAINER_PROFILES = ('ha-cpswms-container-trust-v1', 'ha-cpswms-container-evidence-v2')


def result_index_profile(profile, main_branch):
    if profile not in RESULT_EVENT_PROFILES:
        raise ValueError('unsupported_result_event_profile')
    if (not isinstance(main_branch, str) or not main_branch or len(main_branch) > 512
            or any(ord(character) < 32 for character in main_branch)):
        raise ValueError('invalid_result_main_branch')
    return {'main_branch': main_branch, 'push_events': ['push'],
            'manual_events': ['workflow_dispatch'] if profile == 'legacy-v1' else ['manual'],
            'container_profiles': list(CONTAINER_PROFILES)}
