# v0.3.3
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

@gl.evm.contract_interface
class _Beneficiary:
    class View:
        pass
    class Write:
        pass

class AutonomousDAOGrantExecutive(gl.Contract):
    """
    Autonomous DAO Milestone Grant Executive & Dynamic Slashing Protocol
    
    A standalone GenLayer Intelligent Contract primitive that automates milestone-based
    DAO grants and dynamic slashing. Eliminates centralized committees and human voter fatigue
    by having validators independently acquire live external deliverables (e.g. GitHub repos,
    commit diffs, documentation, CI logs) inside the contract's non-deterministic flow
    via `gl.get_webpage()` and evaluate that acquired material against agreed specifications.
    
    Flow:
    1. DAO / Funder initializes a grant with total tranche funding and an optional performance stake.
    2. Recipient submits milestone deliverable with an external HTTPS verification URL (e.g. raw GitHub/API/doc link).
    3. Independent GenLayer validators fetch the external material evidence directly on-chain via `gl.get_webpage(url)`.
    4. Multi-validator LLMs analyze the acquired content non-deterministically with fail-closed equivalence checks.
    5. Consensus triggers:
       - RELEASE: Current tranche is credited to recipient claimable balance; unlocks next milestone.
       - REVISE: Material evidence requires changes; funds remain locked; recipient can resubmit.
       - SLASH: Fraudulent, malicious, empty, or plagiarized evidence; remaining funds + stake returned to funder.
    6. Clean claimable balance model guarantees non-reentrant reward withdrawals.
    """
    
    admin: Address
    grant_counter: u64
    
    # Grant Configuration & Partakers (keys are string grant_id)
    funders: TreeMap[str, Address]
    recipients: TreeMap[str, Address]
    titles: TreeMap[str, str]
    grant_specifications: TreeMap[str, str]
    
    # Financial State & Conservation of Funds
    total_grant_funds: TreeMap[str, u256]
    locked_grant_funds: TreeMap[str, u256]
    recipient_stakes: TreeMap[str, u256]
    tranche_counts: TreeMap[str, u64]
    current_tranches: TreeMap[str, u64]
    
    # Milestone Tracking & Evidence
    # Grant Status: 0=ACTIVE, 1=MILESTONE_SUBMITTED, 2=COMPLETED, 3=SLASHED_TERMINATED
    grant_statuses: TreeMap[str, u8]
    milestone_deliverables: TreeMap[str, str]
    milestone_proof_urls: TreeMap[str, str]
    acquired_evidence_summaries: TreeMap[str, str]
    latest_verdict_summaries: TreeMap[str, str]
    validator_confidences: TreeMap[str, u8]
    
    # Financial Claimable Balances (Address string -> amount in wei)
    claimable_balances: TreeMap[str, u256]

    def __init__(self):
        self.admin = gl.message.sender_address
        self.grant_counter = 0

    @gl.public.write.payable
    def create_grant(
        self,
        recipient: Address,
        title: str,
        grant_specification: str,
        total_fund_amount: u256,
        tranche_count: u64
    ) -> u64:
        """
        Initializes an autonomous milestone grant backed by locked custody funds.
        """
        funder = gl.message.sender_address
        attached_value = gl.message.value
        
        assert total_fund_amount > 0, "Grant funding amount must exceed zero"
        assert attached_value >= total_fund_amount, f"Attached value {attached_value} is less than required grant funds {total_fund_amount}"
        assert tranche_count > 0, "Milestone tranche count must be at least 1"
        assert len(title.strip()) > 0, "Grant title required"
        assert len(grant_specification.strip()) > 0, "Grant milestone specifications required"
        zero_addr = Address("0x0000000000000000000000000000000000000000")
        assert recipient != zero_addr, "Valid recipient address required"
        
        # Exact accounting / refund excess funds attached
        excess_deposit = attached_value - total_fund_amount
        if excess_deposit > 0:
            _Beneficiary(funder).emit_transfer(value=excess_deposit)
        
        self.grant_counter += 1
        g_id = self.grant_counter
        key = str(g_id)
        
        self.funders[key] = funder
        self.recipients[key] = recipient
        self.titles[key] = title.strip()
        self.grant_specifications[key] = grant_specification.strip()
        self.total_grant_funds[key] = total_fund_amount
        self.locked_grant_funds[key] = total_fund_amount
        self.recipient_stakes[key] = 0
        self.tranche_counts[key] = tranche_count
        self.current_tranches[key] = 1
        
        self.grant_statuses[key] = 0  # ACTIVE
        self.milestone_deliverables[key] = ""
        self.milestone_proof_urls[key] = ""
        self.acquired_evidence_summaries[key] = ""
        self.latest_verdict_summaries[key] = "Grant initialized under autonomous multi-validator milestone supervision."
        self.validator_confidences[key] = 0
        
        return g_id

    @gl.public.write.payable
    def deposit_recipient_stake(self, grant_id: u64, stake_amount: u256) -> None:
        """
        Allows the recipient to deposit performance stake/collateral into the grant.
        """
        sender = gl.message.sender_address
        key = str(grant_id)
        recipient = self.recipients.get(key)
        assert sender == recipient, "Unauthorized: only designated recipient can deposit performance stake"
        
        status = self.grant_statuses.get(key, 255)
        assert status in (0, 1), "Grant is not in an active state"
        
        attached_value = gl.message.value
        assert stake_amount > 0, "Stake amount must exceed zero"
        assert attached_value >= stake_amount, "Attached value does not match declared stake"
        
        cur_stake = self.recipient_stakes.get(key, 0)
        self.recipient_stakes[key] = cur_stake + stake_amount
        
        # Exact accounting / refund excess stake attached
        excess_stake = attached_value - stake_amount
        if excess_stake > 0:
            _Beneficiary(sender).emit_transfer(value=excess_stake)

    @gl.public.write
    def submit_milestone(self, grant_id: u64, deliverable_notes: str, proof_url: str) -> None:
        """
        Recipient submits deliverable notes along with an externally verifiable HTTPS proof URL.
        Validators will autonomously fetch and inspect the content at proof_url during evaluation.
        """
        sender = gl.message.sender_address
        key = str(grant_id)
        recipient = self.recipients.get(key)
        assert sender == recipient, "Unauthorized: caller is not the registered grant recipient"
        
        status = self.grant_statuses.get(key, 255)
        assert status == 0, "Grant must be active and waiting for milestone submission"
        assert len(deliverable_notes.strip()) > 0, "Deliverable notes or description required"
        assert proof_url.strip().startswith("https://"), "Verifiable evidence proof URL must use HTTPS"
        assert len(proof_url.strip()) <= 500, "Proof URL exceeds maximum length"
        
        self.milestone_deliverables[key] = deliverable_notes.strip()
        self.milestone_proof_urls[key] = proof_url.strip()
        self.grant_statuses[key] = 1  # MILESTONE_SUBMITTED
        self.latest_verdict_summaries[key] = f"Milestone tranche #{self.current_tranches.get(key, 1)} submitted with evidence URL. Pending autonomous on-chain web fetch & validator consensus."

    @gl.public.write
    def evaluate_milestone(self, grant_id: u64) -> None:
        """
        Autonomous Multi-Validator Milestone Audit:
        1. Validators independently fetch the material evidence from the submitted HTTPS proof URL using gl.get_webpage().
        2. Validators inspect the acquired material content against the milestone specification.
        3. Validators reach consensus via fail-closed equivalence checks:
           - RELEASE: Disburses current tranche to recipient claimable balance.
           - REVISE: Requests revision from recipient; tranche remains locked.
           - SLASH: Breaches contract; remaining funds + stake returned to funder.
        """
        key = str(grant_id)
        status = self.grant_statuses.get(key, 255)
        assert status == 1, "Milestone must be submitted before evaluation"
        
        title = self.titles.get(key, "")
        spec = self.grant_specifications.get(key, "")
        deliverable_notes = self.milestone_deliverables.get(key, "")
        proof_url = self.milestone_proof_urls.get(key, "")
        cur_tranche = self.current_tranches.get(key, 1)
        tot_tranches = self.tranche_counts.get(key, 1)
        locked_funds = self.locked_grant_funds.get(key, 0)
        recipient = self.recipients.get(key)
        funder = self.funders.get(key)
        stake = self.recipient_stakes.get(key, 0)

        # Capture variables for closure
        captured_title = title
        captured_spec = spec
        captured_notes = deliverable_notes
        captured_url = proof_url
        captured_tranche = cur_tranche
        captured_total_tranches = tot_tranches

        def leader_fn():
            # Step 1: Independently acquire the material evidence on-chain
            acquired_content = ""
            if captured_url.startswith("https://"):
                try:
                    raw_page = gl.nondet.web.render(captured_url, mode="text")
                    acquired_content = raw_page[:4000].strip()
                except Exception as e:
                    acquired_content = f"FETCH_FAILED: {str(e)}"
            
            prompt = f"""You are an autonomous AI Grant Executive and Milestone Auditor on GenLayer.
Evaluate the milestone completion evidence against the grant specifications.
Crucially, review the ACTUAL MATERIAL EVIDENCE acquired on-chain from the external proof URL.

Grant Title: {captured_title}
Grant Specification & Roadmap: {captured_spec}
Current Milestone Tranche: {captured_tranche} of {captured_total_tranches}
Recipient Notes: {captured_notes}
Evidence Proof URL: {captured_url}

ACQUIRED MATERIAL EVIDENCE CONTENT (fetched directly from proof URL):
---
{acquired_content}
---

Evaluation Rules:
1. "RELEASE": The acquired material evidence confirms satisfactory completion of milestone requirements (real code, docs, tests, functional implementation).
2. "REVISE": Evidence is incomplete, fetch returned 404/error, or evidence is partially finished. Recipient may resubmit.
3. "SLASH": Recipient submitted fraudulent, malicious, empty, fake proof URL, or completely failed core objectives.

Respond strictly in valid JSON format:
{{
  "decision": "RELEASE" or "REVISE" or "SLASH",
  "confidence": integer between 60 and 100,
  "reasoning": "Concise justification referencing the acquired evidence content"
}}
"""
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(res, dict):
                raise gl.UserError(f"LLM returned invalid format: {type(res)}")
            
            # Record brief snippet of acquired evidence for on-chain auditability
            res["evidence_snippet"] = acquired_content[:200]
            return res

        def validator_fn(leader_result) -> bool:
            """
            Fail-Closed Substantive Equivalence Check:
            Validators independently fetch the material evidence from the proof URL on their own node,
            execute the LLM audit against the acquired content, and verify matching decision.
            """
            if not isinstance(leader_result, gl.vm.Return):
                return False
            lead_data = leader_result.calldata
            if not isinstance(lead_data, dict):
                return False
                
            lead_decision = str(lead_data.get("decision", "")).strip().upper()
            if lead_decision not in ("RELEASE", "REVISE", "SLASH"):
                return False
                
            lead_reasoning = str(lead_data.get("reasoning", "")).strip()
            if len(lead_reasoning) < 5:
                return False
                
            try:
                # Validator independently acquires material evidence
                val_acquired = ""
                if captured_url.startswith("https://"):
                    try:
                        raw_page = gl.nondet.web.render(captured_url, mode="text")
                        val_acquired = raw_page[:4000].strip()
                    except Exception as e:
                        val_acquired = f"FETCH_FAILED: {str(e)}"

                val_prompt = f"""You are an autonomous AI Grant Executive and Milestone Auditor on GenLayer.
Evaluate the milestone completion evidence against the grant specifications.
Crucially, review the ACTUAL MATERIAL EVIDENCE acquired on-chain from the external proof URL.

Grant Title: {captured_title}
Grant Specification & Roadmap: {captured_spec}
Current Milestone Tranche: {captured_tranche} of {captured_total_tranches}
Recipient Notes: {captured_notes}
Evidence Proof URL: {captured_url}

ACQUIRED MATERIAL EVIDENCE CONTENT (fetched directly from proof URL):
---
{val_acquired}
---

Evaluation Rules:
1. "RELEASE": The acquired material evidence confirms satisfactory completion of milestone requirements.
2. "REVISE": Evidence is incomplete, fetch returned 404/error, or evidence is partially finished. Recipient may resubmit.
3. "SLASH": Recipient submitted fraudulent, malicious, empty, fake proof URL, or completely failed core objectives.

Respond strictly in valid JSON format:
{{
  "decision": "RELEASE" or "REVISE" or "SLASH",
  "confidence": integer between 60 and 100,
  "reasoning": "Concise justification referencing the acquired evidence content"
}}
"""
                val_res = gl.nondet.exec_prompt(val_prompt, response_format="json")
                if isinstance(val_res, dict):
                    val_decision = str(val_res.get("decision", "")).strip().upper()
                    # Substantive equivalence: decisions must match
                    return lead_decision == val_decision
                return False
            except Exception:
                return False

        verdict_res = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        decision = str(verdict_res.get("decision", "")).strip().upper()
        confidence = int(verdict_res.get("confidence", 80))
        reasoning = str(verdict_res.get("reasoning", "AI validator consensus reached on acquired evidence."))
        evidence_snippet = str(verdict_res.get("evidence_snippet", ""))
        
        self.acquired_evidence_summaries[key] = evidence_snippet
        self.validator_confidences[key] = u8(min(100, max(0, confidence)))
        
        if decision == "RELEASE":
            remaining_tranches = (tot_tranches - cur_tranche) + 1
            tranche_payout = locked_funds // remaining_tranches
            if cur_tranche == tot_tranches:
                tranche_payout = locked_funds
                
            self.locked_grant_funds[key] = locked_funds - tranche_payout
            cur_recip_bal = self.claimable_balances.get(str(recipient), 0)
            self.claimable_balances[str(recipient)] = cur_recip_bal + tranche_payout
            
            if cur_tranche >= tot_tranches:
                self.grant_statuses[key] = 2  # COMPLETED
                if stake > 0:
                    self.recipient_stakes[key] = 0
                    self.claimable_balances[str(recipient)] = self.claimable_balances.get(str(recipient), 0) + stake
                self.latest_verdict_summaries[key] = f"Final milestone approved ({confidence}% consensus): {reasoning}. Full grant successfully completed and stake unlocked."
            else:
                self.current_tranches[key] = cur_tranche + 1
                self.grant_statuses[key] = 0  # ACTIVE for next tranche
                self.milestone_deliverables[key] = ""
                self.milestone_proof_urls[key] = ""
                self.latest_verdict_summaries[key] = f"Milestone tranche #{cur_tranche} approved ({confidence}% consensus): {reasoning}. Awarded {tranche_payout} wei. Proceed to tranche #{cur_tranche + 1}."

        elif decision == "SLASH":
            self.grant_statuses[key] = 3  # SLASHED_TERMINATED
            refund_amount = locked_funds + stake
            self.locked_grant_funds[key] = 0
            self.recipient_stakes[key] = 0
            
            cur_funder_bal = self.claimable_balances.get(str(funder), 0)
            self.claimable_balances[str(funder)] = cur_funder_bal + refund_amount
            
            self.latest_verdict_summaries[key] = f"Milestone rejected and slashed ({confidence}% consensus): {reasoning}. Refunded {refund_amount} wei (remaining grant + stake) to funder."
            
        else:  # REVISE
            self.grant_statuses[key] = 0  # Reopen for revision
            self.latest_verdict_summaries[key] = f"Revision requested ({confidence}% consensus): {reasoning}. Tranche locked pending revised evidence submission."

    @gl.public.write
    def revoke_grant(self, grant_id: u64) -> None:
        """
        Allows the funder to cancel an active grant and reclaim unreleased tranches.
        """
        sender = gl.message.sender_address
        key = str(grant_id)
        funder = self.funders.get(key)
        assert sender == funder, "Unauthorized: only the grant funder can revoke"
        
        status = self.grant_statuses.get(key, 255)
        assert status == 0, "Can only revoke grant while in active status and between milestones"
        
        remaining = self.locked_grant_funds.get(key, 0)
        assert remaining > 0, "No remaining funds to refund"
        
        self.locked_grant_funds[key] = 0
        self.grant_statuses[key] = 3  # TERMINATED
        
        stake = self.recipient_stakes.get(key, 0)
        if stake > 0:
            self.recipient_stakes[key] = 0
            recipient = self.recipients.get(key)
            self.claimable_balances[str(recipient)] = self.claimable_balances.get(str(recipient), 0) + stake
            
        cur_funder_bal = self.claimable_balances.get(str(funder), 0)
        self.claimable_balances[str(funder)] = cur_funder_bal + remaining
        
        self.latest_verdict_summaries[key] = f"Grant revoked by funder. Refunded {remaining} wei unreleased tranches to funder."

    @gl.public.write
    def withdraw_funds(self, beneficiary: Address) -> u256:
        """
        Authorizes beneficiary to withdraw settled balances.
        Transfers the native GEN value to the beneficiary via _Beneficiary emit_transfer.
        """
        sender = gl.message.sender_address
        assert sender == beneficiary, "Unauthorized: caller can only withdraw their own claimable balance"
        
        balance = self.claimable_balances.get(str(beneficiary), 0)
        assert balance > 0, "No claimable balance available for withdrawal"
        
        self.claimable_balances[str(beneficiary)] = 0
        _Beneficiary(beneficiary).emit_transfer(value=balance)
        return balance

    @gl.public.view
    def get_grant(self, grant_id: u64) -> dict:
        key = str(grant_id)
        zero_addr = Address("0x0000000000000000000000000000000000000000")
        return {
            "id": grant_id,
            "funder": str(self.funders.get(key, zero_addr)),
            "recipient": str(self.recipients.get(key, zero_addr)),
            "title": self.titles.get(key, ""),
            "specification": self.grant_specifications.get(key, ""),
            "total_funds": str(self.total_grant_funds.get(key, 0)),
            "locked_funds": str(self.locked_grant_funds.get(key, 0)),
            "recipient_stake": str(self.recipient_stakes.get(key, 0)),
            "tranche_count": self.tranche_counts.get(key, 1),
            "current_tranche": self.current_tranches.get(key, 1),
            "status": self.grant_statuses.get(key, 0),
            "deliverable": self.milestone_deliverables.get(key, ""),
            "proof_url": self.milestone_proof_urls.get(key, ""),
            "acquired_evidence_snippet": self.acquired_evidence_summaries.get(key, ""),
            "verdict_summary": self.latest_verdict_summaries.get(key, ""),
            "validator_confidence": self.validator_confidences.get(key, 0)
        }

    @gl.public.view
    def get_claimable_balance(self, user: Address) -> str:
        return str(self.claimable_balances.get(str(user), 0))

    @gl.public.view
    def get_total_grants(self) -> u64:
        return self.grant_counter
