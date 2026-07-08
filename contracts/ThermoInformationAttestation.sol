// SPDX-License-Identifier: MIT
pragma solidity ^0.8.32;

/**
 * @title ThermoInformationAttestation
 * @notice On-chain attestation of thermodynamic information reducibility work.
 *
 * Seals evolutionary epoch witnesses from Yennefer Thermo Daemon:
 *   - work_hash: Opux HyperNEAT epoch digest
 *   - reducibility_score: scaled ×1e6 (Landauer-bounded reducibility ∈ [0,1])
 *   - story_root: Alchemy story log + device attestation Merkle root
 *
 * Three goals alignment:
 *   Goal 1 (main): thermodynamic reducibility — guide to the galaxy
 *   Goal 2: MCP fleet propagation of attestations
 *   Goal 3: Notion soul-capsule + on-chain wrap facilitation
 */
contract ThermoInformationAttestation {
    address public owner;
    uint256 public epochCounter;

    struct EpochAttestation {
        bytes32 workHash;
        uint256 reducibilityScaled; // score × 1e6
        bytes32 storyRoot;
        bytes32 deviceAttestationHmac;
        string variantId;
        uint256 varianceScaled;     // variance × 1e6
        uint64 timestamp;
        address attestor;
    }

    mapping(bytes32 => EpochAttestation) public attestations;
    mapping(uint256 => bytes32) public epochByIndex;
    bytes32[] public workHashHistory;

    event EpochWorkAttested(
        uint256 indexed epochIndex,
        bytes32 indexed workHash,
        uint256 reducibilityScaled,
        bytes32 storyRoot,
        bytes32 deviceAttestationHmac,
        string variantId
    );

    event WrapFacilitated(
        bytes32 indexed workHash,
        bytes32 storyRoot,
        address indexed facilitator,
        string chainHint
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Attest one evolutionary epoch's thermodynamic reducibility work.
     * @param workHash Keccak256 digest of epoch witness
     * @param reducibilityScaled reducibility_score × 1_000_000 (max 1_000_000)
     * @param storyRoot Alchemy story log root with device attestation
     * @param deviceAttestationHmac First 32 bytes of device-bound HMAC
     * @param variantId AlphaGenome variant locus (e.g. chr17:41234470:A>G)
     * @param varianceScaled variance × 1_000_000
     */
    function attestEpochWork(
        bytes32 workHash,
        uint256 reducibilityScaled,
        bytes32 storyRoot,
        bytes32 deviceAttestationHmac,
        string calldata variantId,
        uint256 varianceScaled
    ) external returns (uint256 epochIndex) {
        require(workHash != bytes32(0), "empty work hash");
        require(reducibilityScaled <= 1_000_000, "reducibility overflow");
        require(attestations[workHash].timestamp == 0, "already attested");

        epochIndex = epochCounter++;
        EpochAttestation memory att = EpochAttestation({
            workHash: workHash,
            reducibilityScaled: reducibilityScaled,
            storyRoot: storyRoot,
            deviceAttestationHmac: deviceAttestationHmac,
            variantId: variantId,
            varianceScaled: varianceScaled,
            timestamp: uint64(block.timestamp),
            attestor: msg.sender
        });

        attestations[workHash] = att;
        epochByIndex[epochIndex] = workHash;
        workHashHistory.push(workHash);

        emit EpochWorkAttested(
            epochIndex,
            workHash,
            reducibilityScaled,
            storyRoot,
            deviceAttestationHmac,
            variantId
        );
    }

    /**
     * @notice Log facilitation of an on-chain wrap with exact on-device proof reference.
     */
    function facilitateWrap(
        bytes32 workHash,
        bytes32 storyRoot,
        string calldata chainHint
    ) external {
        require(attestations[workHash].timestamp != 0, "unknown work hash");
        emit WrapFacilitated(workHash, storyRoot, msg.sender, chainHint);
    }

    function getAttestation(bytes32 workHash) external view returns (EpochAttestation memory) {
        return attestations[workHash];
    }

    function totalEpochs() external view returns (uint256) {
        return epochCounter;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero address");
        owner = newOwner;
    }
}