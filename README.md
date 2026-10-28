# Autonomous DAO Grant Executive

An Autonomous, Multi-Validator Milestone Grant Evaluation & Dynamic Slashing Intelligent Contract deployed on GenLayer Studio Next (Chain ID `61997`).

## Overview
Traditional DAO grants suffer from high coordination overhead, governance fatigue, subjective milestone sign-offs, and delayed disbursements. **AutonomousDAOGrantExecutive** solves this by leveraging GenLayer's non-deterministic Intelligent Contracts. Independent LLM validators directly acquire external evidence on-chain via `gl.nondet.web.render()` and reach decentralized consensus over submitted milestone deliverables against the original specification, unlocking tranches or slashing fraudulent submissions autonomously.

## Verified On-Chain Deployment
- **Network**: GenLayer Studio Next (Chain ID: `61997`)
- **Contract Address**: [`0x315241872CE62F5c36D042FA4Ee63D8c5b96fe37`](https://explorer-studio-dev.genlayer.com/address/0x315241872CE62F5c36D042FA4Ee63D8c5b96fe37)
- **Explorer URL**: https://explorer-studio-dev.genlayer.com/address/0x315241872CE62F5c36D042FA4Ee63D8c5b96fe37

## Key Architecture & Features
1. **On-Chain Evidence Acquisition (`gl.nondet.web.render`)**: Validators autonomously fetch live material evidence from external HTTPS URLs directly inside the contract's non-deterministic execution flow before performing any evaluation.
2. **Substantive Non-Deterministic Multi-Validator Consensus**: Uses `gl.vm.run_nondet_unsafe` where leader and validator LLMs independently grade acquired deliverables with strict fail-closed equivalence checks on verdict status, confidence threshold (>=75%), and substantive semantic rationales.
3. **Exact Accounting & Excess Deposit Refund**: Both `create_grant` and `deposit_recipient_stake` calculate any excess deposit beyond the required amount (`attached_value - declared_amount`) and immediately refund it via `_Beneficiary.emit_transfer`.
4. **Contract-Native Value Transfer via `emit_transfer`**: Calling `withdraw_funds` zeros the claimable balance and directly transfers native GEN to the recipient's wallet via `_Beneficiary(beneficiary).emit_transfer(value=balance)`.
5. **Dynamic Slashing & Revocation**: Slashes recipient stake upon fraudulent or malicious deliverables and allows the funder to revoke unreleased tranches.
6. **Collision-Proof Storage**: Clean state design utilizing isolated `TreeMap` collections.

## Live On-Chain Activity (Studio Next 61997)
- **Contract Address**: `0x315241872CE62F5c36D042FA4Ee63D8c5b96fe37`
- **Deployment Transaction**: `0x753c043ec39ba55291c4909ea2f0c71b9967bbd8bcd47593e9f17345da118f60`
- **Grant Creation**: `0x3e5d57cfdf0bc27dd815510900580eef46e9d654d926fc89abf34d2f934d3b33` (0.1 GEN locked)
- **Milestone Submission**: `0xccbe998c1bb6bb5e5e53c4dd48f1c42d6d06e00fd49ab2743de59755ccdb8025`
- **Autonomous AI Consensus Evaluation (Evidence Fetched On-Chain)**: `0xeb7bd8c448e5fec9df823ce45ec109186348ccce753a1363471ae5bdb03fbbae` (Approved with 95% validator consensus, 0.05 GEN tranche unlocked on-chain).
- **Native Fund Withdrawal via `emit_transfer`**: `0x9c672a0a70016787dd37dd428990d3832a8034dc2e20177aacd837c81f90467f` (0.05 GEN transferred directly to recipient wallet).

## License
MIT
