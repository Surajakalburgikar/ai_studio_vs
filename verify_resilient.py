import os
import sys
import time
import subprocess
import unittest
import re
import socket

def classify_provider_exception(e: Exception) -> str:
    err_msg = str(e).lower()
    
    # 1. Rate Limit
    if "429" in err_msg or "rate limit" in err_msg or "too many requests" in err_msg:
        return "rate_limited"
        
    # 2. Quota / Credits / Billing
    if "quota" in err_msg or "exhausted" in err_msg or "credit" in err_msg or "billing" in err_msg or "402" in err_msg:
        return "quota_exhausted"
        
    # 3. Invalid Configuration / Credentials / API Keys
    if "401" in err_msg or "403" in err_msg or "unauthorized" in err_msg or "api key" in err_msg or "invalid key" in err_msg or "credentials" in err_msg or "token" in err_msg:
        if "quota" in err_msg or "limit" in err_msg or "exhausted" in err_msg:
            return "quota_exhausted"
        return "invalid_config"
        
    # 4. Network / Timeout / DNS
    if isinstance(e, (TimeoutError, socket.timeout)) or "timeout" in err_msg or "timed out" in err_msg:
        return "network_error"
    if "connection" in err_msg or "dns" in err_msg or "network" in err_msg or "unreachable" in err_msg or "host" in err_msg:
        return "network_error"
        
    # 5. Invalid parameters / Bad Requests
    if "400" in err_msg or "bad request" in err_msg or "invalid parameters" in err_msg:
        return "invalid_config"
        
    return "invalid_config"


def run_with_retry_policy(func, max_retries=3, initial_delay=1.0):
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            classification = classify_provider_exception(e)
            if classification == "network_error" and attempt < max_retries:
                print(f"[Retry] Network error on attempt {attempt+1}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2.0
            else:
                raise e


def verify_real_story_provider():
    sys.path.append(os.path.abspath("."))
    from app.services.ai.providers.gemini_provider import GeminiProvider
    provider = GeminiProvider()
    response = provider.generate("Write a 1-sentence fantasy summary.")
    if not response or len(response.strip()) == 0:
        raise ValueError("Empty response from Gemini")
    return response


def verify_real_image_provider():
    sys.path.append(os.path.abspath("."))
    sys.path.append(os.path.abspath("../AI_STUDIO_WORKER"))
    from worker.image_providers.flux_provider import FluxProvider
    from worker.models.job import GenerationJob
    
    job = GenerationJob(
        id=9999,
        scene_id=1,
        shot_number=1,
        provider="flux",
        prompt="A single red apple on a wooden table, anime style",
        negative_prompt="blurry, low quality",
        filename="test_real_provider_verify.png",
        status="pending",
        priority=0,
        retry_count=0,
        progress=0
    )
    provider = FluxProvider()
    img = provider.generate(job)
    if img is None:
        raise ValueError("Flux generated a None image")
    return img


class TestRealProviderIntegration(unittest.TestCase):
    
    def test_real_story_provider(self):
        if not os.environ.get("VERIFY_REAL_PROVIDER") == "true":
            self.skipTest("Real provider verification disabled (VERIFY_REAL_PROVIDER=true not set)")
            
        try:
            run_with_retry_policy(verify_real_story_provider)
        except Exception as e:
            classification = classify_provider_exception(e)
            if classification == "rate_limited":
                self.skipTest("Provider rate limited")
            elif classification == "quota_exhausted":
                self.skipTest("Daily quota exhausted")
            elif classification == "network_error":
                self.skipTest("Network failure after retries")
            else:
                self.fail(f"Invalid Configuration: {str(e)}")

    def test_real_image_provider(self):
        if not os.environ.get("VERIFY_REAL_PROVIDER") == "true":
            self.skipTest("Real provider verification disabled (VERIFY_REAL_PROVIDER=true not set)")
            
        try:
            run_with_retry_policy(verify_real_image_provider)
        except Exception as e:
            classification = classify_provider_exception(e)
            if classification == "rate_limited":
                self.skipTest("Provider rate limited")
            elif classification == "quota_exhausted":
                self.skipTest("Daily quota exhausted")
            elif classification == "network_error":
                self.skipTest("Network failure after retries")
            else:
                self.fail(f"Invalid Configuration: {str(e)}")


def parse_unittest_output(output):
    # Find "Ran X tests"
    ran_match = re.search(r"Ran (\d+) tests", output)
    if not ran_match:
        return None
        
    ran = int(ran_match.group(1))
    skipped = 0
    failures = 0
    errors = 0
    
    skipped_match = re.search(r"skipped=(\d+)", output)
    if skipped_match:
        skipped = int(skipped_match.group(1))
        
    failures_match = re.search(r"failures=(\d+)", output)
    if failures_match:
        failures = int(failures_match.group(1))
        
    errors_match = re.search(r"errors=(\d+)", output)
    if errors_match:
        errors = int(errors_match.group(1))
        
    failed = failures + errors
    passed = ran - failed - skipped
    return {"ran": ran, "passed": passed, "failed": failed, "skipped": skipped}


def format_skip_reason(reason):
    reason_lower = reason.lower()
    if "rate" in reason_lower:
        return "Rate Limited"
    if "quota" in reason_lower or "exhausted" in reason_lower or "credit" in reason_lower:
        return "Quota Exhausted"
    if "network" in reason_lower or "timeout" in reason_lower or "connection" in reason_lower:
        return "Network Error"
    return "Skipped"


class ResilientTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_skips = []
        self.custom_failures = []
        self.custom_successes = []

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.custom_skips.append((test, reason))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.custom_failures.append((test, err))

    def addError(self, test, err):
        super().addError(test, err)
        self.custom_failures.append((test, err))

    def addSuccess(self, test):
        super().addSuccess(test)
        self.custom_successes.append(test)


def main():
    print("AI Studio Resilient Verification Suite Started")
    print("------------------------------------------------------------")
    
    # ------------------------------------------------------------
    # MODE 1 — Pipeline Verification (Default)
    # ------------------------------------------------------------
    print("MODE 1 — Running Pipeline Verification (Default)...")
    
    env_vars = os.environ.copy()
    env_vars["VERIFY_PIPELINE"] = "true"
    
    pipeline_scripts = [
        "verify_pipeline_contract.py",
        "verify_sprint_30.py",
        "verify_sprint30_1.py"
    ]
    
    passed_pipeline = 0
    failed_pipeline = 0
    skipped_pipeline = 0
    
    for script in pipeline_scripts:
        if not os.path.exists(script):
            print(f"[Warning] Script not found: {script}")
            continue
            
        print(f"\nRunning {script}...")
        t0 = time.time()
        
        # Run script in subprocess
        res = subprocess.run([sys.executable, script], capture_output=True, text=True, env=env_vars)
        duration = time.time() - t0
        print(f"Finished {script} in {duration:.2f}s (Exit code: {res.returncode})")
        
        # Parse the output
        output_text = res.stdout + "\n" + res.stderr
        stats = parse_unittest_output(output_text)
        
        if stats:
            print(f"Results: {stats['passed']} Passed, {stats['failed']} Failed, {stats['skipped']} Skipped")
            passed_pipeline += stats["passed"]
            failed_pipeline += stats["failed"]
            skipped_pipeline += stats["skipped"]
        else:
            # Fallback if parsing failed
            if res.returncode == 0:
                print("Results: All tests passed (parsing output failed)")
                passed_pipeline += 1
            else:
                print("Results: Script failed execution")
                failed_pipeline += 1
                
        # Sleep briefly to ensure TIME_WAIT sockets release
        time.sleep(1.0)
        
    # ------------------------------------------------------------
    # MODE 2 — Real Provider Verification
    # ------------------------------------------------------------
    print("\nMODE 2 — Running Real Provider Verification...")
    
    real_provider_enabled = os.environ.get("VERIFY_REAL_PROVIDER") == "true"
    
    passed_provider = 0
    failed_provider = 0
    skipped_provider = 0
    skip_reasons = []
    
    if not real_provider_enabled:
        print("Real provider verification is disabled (VERIFY_REAL_PROVIDER=true not set). Skipping.")
        skipped_provider = 2
        skip_reasons = ["Disabled", "Disabled"]
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestRealProviderIntegration)
        runner = unittest.TextTestRunner(resultclass=ResilientTestResult)
        result = runner.run(suite)
        
        passed_provider = len(result.custom_successes)
        failed_provider = len(result.custom_failures)
        skipped_provider = len(result.custom_skips)
        for _, reason in result.custom_skips:
            skip_reasons.append(format_skip_reason(reason))
            
    # ------------------------------------------------------------
    # Print Final Verification Report
    # ------------------------------------------------------------
    print("\n" + "=" * 60)
    print("VERIFICATION REPORT")
    print("=" * 60)
    print("Pipeline Tests")
    print(f"  {passed_pipeline} Passed")
    print(f"  {failed_pipeline} Failed")
    if skipped_pipeline > 0:
        print(f"  {skipped_pipeline} Skipped")
        
    print("\nReal Provider Tests")
    if real_provider_enabled:
        print(f"  {passed_provider} Passed")
        print(f"  {failed_provider} Failed")
        if skipped_provider > 0:
            reasons_str = ", ".join(skip_reasons)
            print(f"  {skipped_provider} Skipped ({reasons_str})")
    else:
        print(f"  {skipped_provider} Skipped (Disabled)")
        
    print("-" * 60)
    
    # Overall Result
    if failed_pipeline > 0 or failed_provider > 0:
        print("Overall Result: FAILED")
        sys.exit(1)
    else:
        print("Overall Result")
        print("  Pipeline Verified Successfully")
        if skipped_provider > 0:
            if not real_provider_enabled:
                print("  External provider tests were disabled.")
            else:
                print("  External provider unavailable during optional integration tests.")
        sys.exit(0)


if __name__ == "__main__":
    main()
