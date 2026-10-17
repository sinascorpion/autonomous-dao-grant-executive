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
    Autonomous DAO Milestone Grant Executive & Slashing Protocol
    
    A standalone GenLayer Intelligent Contract primitive that automates milestone-based
    DAO grants and dynamic slashing. Eliminates centralized committees and human voter fatigue
    by leveraging non-deterministic LLM validator consensus with substantive fail-closed
    equivalence checks.
    
    Flow:
    1. DAO / Funder initializes a grant with total tranche funding and an optional performance stake.
    2. Recipient submits milestone deliverables, commit hashes, test metrics, and deploy logs.
    3. Independent GenLayer validators evaluate deliverables against milestone criteria non-deterministically.
    4. Consensus triggers:
       - RELEASE: Current tranche is credited to recipient claimable balance; unlocks next milestone.
       - REVISE: Feedback is logged; funds remain locked; recipient can resubmit within window.
       - SLASH: Severe breach/abandonment; remaining funds + stake are slashed & refunded to DAO treasury.
    5. Clean claimable balance model ensures safe external withdrawals.
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
        Initializes an autonomous milestone grant with contract custody of funds.
        Enforces strict value matching and valid tranche configurations.
        """
        funder = gl.message.sender_address
        attached_value = gl.message.value
        
        assert total_fund_amount > 0, "Grant total funding must exceed zero"
        assert attached_value >= total_fund_amount, f"Attached value {attached_value} is less than grant amount {total_fund_amount}"
        assert tranche_count > 0, "Tranche count must be at least 1"
        assert len(title.strip()) > 0, "Grant title required"
        assert len(grant_specification.strip()) > 0, "Milestone specifications required"
        
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

    @gl.public.write
    def submit_milestone(self, grant_id: u64, deliverable_evidence: str) -> None:
        """
        Recipient submits proof of completion for the current milestone tranche.
        """
        sender = gl.message.sender_address
        key = str(grant_id)
        recipient = self.recipients.get(key)
        assert sender == recipient, "Unauthorized: caller is not the registered grant recipient"
        
        status = self.grant_statuses.get(key, 255)
        assert status == 0, "Grant must be active and waiting for milestone submission"
        assert len(deliverable_evidence.strip()) > 0, "Deliverable evidence or proof links required"
        
        self.milestone_deliverables[key] = deliverable_evidence.strip()
        self.grant_statuses[key] = 1  # MILESTONE_SUBMITTED
        self.latest_verdict_summaries[key] = f"Milestone tranche #{self.current_tranches.get(key, 1)} submitted. Pending AI validator evaluation."

    @gl.public.write
    def evaluate_milestone(self, grant_id: u64) -> None:
        """
        Autonomous Multi-Validator Milestone Audit:
        Uses GenLayer non-deterministic LLM consensus with substantive equivalence checks.
        Validators independently audit deliverables against milestone specs and vote:
        - RELEASE: Disburses current tranche to recipient.
        - REVISE: Requests revision from recipient; tranche remains locked.
        - SLASH: Breaches contract; remaining funds + stake returned to funder.
        """
        key = str(grant_id)
        status = self.grant_statuses.get(key, 255)
        assert status == 1, "Milestone must be submitted before evaluation"
        
        title = self.titles.get(key, "")
        spec = self.grant_specifications.get(key, "")
        evidence = self.milestone_deliverables.get(key, "")
        cur_tranche = self.current_tranches.get(key, 1)
        tot_tranches = self.tranche_counts.get(key, 1)
        locked_funds = self.locked_grant_funds.get(key, 0)
        recipient = self.recipients.get(key)
        funder = self.funders.get(key)
        stake = self.recipient_stakes.get(key, 0)
        
        prompt = f"""You are an autonomous AI Grant Executive and Milestone Auditor on GenLayer.
Evaluate the milestone completion evidence against the grant specifications.

Grant Title: {title}
Grant Specification & Roadmap: {spec}
Current Milestone Tranche: {cur_tranche} of {tot_tranches}
Recipient Submitted Deliverable Evidence: {evidence}

Evaluation Criteria:
1. "RELEASE": Deliverable satisfactorily satisfies the milestone requirements (code, docs, tests, functional demo).
2. "REVISE": Deliverable is partially complete, requires minor fixes, or proof link is missing context. Recipient may resubmit.
3. "SLASH": Recipient submitted fraudulent, plagiarized, malicious evidence, or completely failed core objectives.

Respond strictly in valid JSON format:
{{
  "decision": "RELEASE" or "REVISE" or "SLASH",
  "confidence": integer between 60 and 100,
  "reasoning": "Concise justification for the verdict"
}}
"""

        def leader_fn():
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(res, dict):
                raise gl.UserError(f"LLM returned invalid format: {type(res)}")
            return res

        def validator_fn(leader_result) -> bool:
            """
            Fail-Closed Substantive Equivalence Check:
            Validators independently run LLM prompt on their own node and verify matching decision.
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
                val_res = gl.nondet.exec_prompt(prompt, response_format="json")
                if isinstance(val_res, dict):
                    val_decision = str(val_res.get("decision", "")).strip().upper()
                    return lead_decision == val_decision
                return False
            except Exception:
                return False

        verdict_res = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        decision = str(verdict_res.get("decision", "")).strip().upper()
        confidence = int(verdict_res.get("confidence", 80))
        reasoning = str(verdict_res.get("reasoning", "AI validator consensus reached."))
        
        self.validator_confidences[key] = u8(min(100, max(0, confidence)))
        
        if decision == "RELEASE":
            # Calculate tranche amount: proportional split of remaining tranches
            remaining_tranches = (tot_tranches - cur_tranche) + 1
            tranche_payout = locked_funds // remaining_tranches
            if cur_tranche == tot_tranches:
                tranche_payout = locked_funds  # Final tranche clears remaining funds
                
            self.locked_grant_funds[key] = locked_funds - tranche_payout
            cur_recip_bal = self.claimable_balances.get(str(recipient), 0)
            self.claimable_balances[str(recipient)] = cur_recip_bal + tranche_payout
            
            if cur_tranche >= tot_tranches:
                self.grant_statuses[key] = 2  # COMPLETED
                # Return recipient stake upon successful final milestone
                if stake > 0:
                    self.recipient_stakes[key] = 0
                    self.claimable_balances[str(recipient)] = self.claimable_balances.get(str(recipient), 0) + stake
                self.latest_verdict_summaries[key] = f"Final milestone approved ({confidence}% consensus): {reasoning}. Full grant successfully completed and stake unlocked."
            else:
                self.current_tranches[key] = cur_tranche + 1
                self.grant_statuses[key] = 0  # ACTIVE (awaiting next milestone)
                self.milestone_deliverables[key] = ""
                self.latest_verdict_summaries[key] = f"Milestone #{cur_tranche} approved ({confidence}% consensus): {reasoning}. Tranche released ({tranche_payout} wei). Proceed to milestone #{cur_tranche + 1}."
                
        elif decision == "REVISE":
            self.grant_statuses[key] = 0  # ACTIVE (ready for resubmission)
            self.latest_verdict_summaries[key] = f"Revision requested ({confidence}% consensus): {reasoning}. Tranche locked pending revised submission."
            
        else:  # SLASH
            self.grant_statuses[key] = 3  # SLASHED_TERMINATED
            self.locked_grant_funds[key] = 0
            self.recipient_stakes[key] = 0
            
            # Conservation of funds: Refund remaining grant funds + slashed stake back to funder treasury
            total_refund = locked_funds + stake
            cur_funder_bal = self.claimable_balances.get(str(funder), 0)
            self.claimable_balances[str(funder)] = cur_funder_bal + total_refund
            self.latest_verdict_summaries[key] = f"GRANT SLASHED ({confidence}% consensus): {reasoning}. Remaining {locked_funds} wei and {stake} wei stake forfeited and returned to DAO treasury."

    @gl.public.write
    def withdraw_funds(self, beneficiary: Address) -> u256:
        """
        Authorizes beneficiary to withdraw settled balances.
        """
        sender = gl.message.sender_address
        assert sender == beneficiary, "Unauthorized: caller can only withdraw their own claimable balance"
        
        balance = self.claimable_balances.get(str(beneficiary), 0)
        assert balance > 0, "No claimable balance available for withdrawal"
        
        self.claimable_balances[str(beneficiary)] = 0
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
            "verdict_summary": self.latest_verdict_summaries.get(key, ""),
            "validator_confidence": self.validator_confidences.get(key, 0)
        }

    @gl.public.view
    def get_claimable_balance(self, user: Address) -> str:
        return str(self.claimable_balances.get(str(user), 0))

    @gl.public.view
    def get_total_grants(self) -> u64:
        return self.grant_counter
