from src.security.guardrails import GuardrailsService

service = GuardrailsService()
results = service.test_malicious_prompts()

print("Detailed results for malicious prompts that should be blocked:")
for detail in results['details']:
    if detail['should_block'] and not detail['was_blocked']:
        print(f"MISSED: {detail['prompt']} (type: {detail['attack_type']})")
    elif detail['should_block'] and detail['was_blocked']:
        print(f"CAUGHT: {detail['attack_type']}")

print(f"\nSummary: {results['accuracy']:.1%} accuracy, {len([d for d in results['details'] if d['should_block'] and d['was_blocked']])}/{len([d for d in results['details'] if d['should_block']])} malicious blocked")