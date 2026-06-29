"""
ingest_tspec.py — ingestion pipeline for the TSpec-LLM dataset.

Steps:
  1. Load rasoul-nikbakht/TSpec-LLM from HuggingFace (or fallback mock data)
  2. Inspect schema and auto-detect text fields
  3. Extract a small sample suitable for local development
  4. Save a JSON preview to data/raw/tspec_sample/
  5. Chunk the text with RecursiveCharacterTextSplitter
  6. Embed with all-MiniLM-L6-v2 (local) or OpenAI
  7. Store embeddings in ChromaDB

Usage:
    python -m app.rag.ingest_tspec           # uses HuggingFace dataset
    python -m app.rag.ingest_tspec --mock    # uses built-in mock docs
    python -m app.rag.ingest_tspec --reset   # clears ChromaDB before ingesting
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.rag.chunking import chunk_documents
from app.rag.embeddings import get_embeddings
from app.rag.vector_store import (
    delete_collection,
    get_chroma_client,
    get_or_create_collection,
)
from app.services.config import (
    CHROMA_COLLECTION,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    TSPEC_DATASET,
    TSPEC_SAMPLE_SIZE,
)
from app.utils.logger import setup_logger

log = setup_logger("ingest")

# ── Built-in mock documents ──────────────────────────────────────────────────
# Used as fallback when the HuggingFace dataset cannot be downloaded.
# Covers the most common telecom topics students will demo.

MOCK_DOCS: List[Dict[str, Any]] = [
    {
        "text": (
            "5G NR (New Radio) is the global standard for a unified, more capable 5G wireless air interface, "
            "defined by 3GPP starting from Release 15 (2018). It operates in two frequency ranges: "
            "FR1 (sub-6 GHz, 410 MHz – 7.125 GHz) and FR2 (millimetre wave, 24.25 – 52.6 GHz). "
            "5G NR supports three primary use cases: enhanced Mobile Broadband (eMBB) for extreme data rates, "
            "Ultra-Reliable Low-Latency Communication (URLLC) targeting sub-1 ms latency, "
            "and massive Machine-Type Communication (mMTC) for IoT. "
            "Peak downlink throughput targets 20 Gbps (eMBB). Defined in 3GPP TS 38.300."
        ),
        "metadata": {"source": "3GPP_TS38.300", "topic": "5G NR Overview", "spec": "TS 38.300", "release": "15"},
    },
    {
        "text": (
            "The 5G core network (5GC) follows a Service-Based Architecture (SBA) where network functions (NFs) "
            "expose services via RESTful HTTP/2 APIs. Key NFs: "
            "AMF (Access and Mobility Management Function) handles NAS signalling and UE registration; "
            "SMF (Session Management Function) manages PDU sessions and IP address allocation; "
            "UPF (User Plane Function) routes user-plane traffic; "
            "PCF (Policy Control Function) provides QoS policies; "
            "UDM (Unified Data Management) stores subscriber data; "
            "AUSF (Authentication Server Function) performs authentication. "
            "Xn interface: between gNBs. N2: gNB–AMF. N3: gNB–UPF. N4: SMF–UPF. Defined in TS 23.501."
        ),
        "metadata": {"source": "3GPP_TS23.501", "topic": "5G Core Network (5GC)", "spec": "TS 23.501", "release": "15"},
    },
    {
        "text": (
            "LTE (Long Term Evolution) — also called 4G LTE — is standardised in 3GPP Release 8 (2008). "
            "The air interface is E-UTRA (Evolved Universal Terrestrial Radio Access). "
            "LTE uses OFDMA in the downlink and SC-FDMA in the uplink. "
            "Supported bandwidths: 1.4, 3, 5, 10, 15, 20 MHz. "
            "LTE-Advanced (Release 10, 2011) added carrier aggregation (up to 100 MHz total), "
            "CoMP (Coordinated Multi-Point), and enhanced MIMO. "
            "LTE-Advanced Pro (Release 13+) added NB-IoT, eMTC, and LAA. "
            "Peak downlink: 300 Mbps (LTE Cat-6), 3 Gbps (LTE-Advanced Pro). Defined in TS 36.300."
        ),
        "metadata": {"source": "3GPP_TS36.300", "topic": "LTE (4G)", "spec": "TS 36.300", "release": "8"},
    },
    {
        "text": (
            "Massive MIMO (Multiple Input Multiple Output) is a key 5G NR technology using antenna arrays "
            "with 32–256 antenna elements at the gNB. "
            "Beamforming steers energy towards individual UEs using phase and amplitude control. "
            "5G NR supports up to 8 downlink MIMO layers (rank-8 DL) and 4 uplink layers. "
            "Full Dimension MIMO (FD-MIMO) supports 3D beamforming (both azimuth and elevation steering). "
            "Codebook-based precoding uses SRS (Sounding Reference Signals) and CSI-RS for channel estimation. "
            "Non-codebook precoding allows the UE to suggest a precoder. Defined in TS 38.214."
        ),
        "metadata": {"source": "3GPP_TS38.214", "topic": "Massive MIMO and Beamforming", "spec": "TS 38.214", "release": "15"},
    },
    {
        "text": (
            "5G NR physical layer numerology is defined in TS 38.211. "
            "Subcarrier spacing (SCS) options: 15 kHz, 30 kHz, 60 kHz (FR1); 60 kHz, 120 kHz (FR2); 240 kHz (FR2 reference). "
            "Slot duration: 1 ms (15 kHz SCS), 0.5 ms (30 kHz), 0.25 ms (60 kHz), 0.125 ms (120 kHz). "
            "A radio frame is 10 ms; a subframe is 1 ms; each subframe contains 2^μ slots (μ = numerology index). "
            "Mini-slots (2, 4, or 7 OFDM symbols) reduce scheduling latency for URLLC. "
            "Both FDD and TDD are supported. Cyclic prefix: normal (14 OFDM symbols/slot) or extended (12 symbols)."
        ),
        "metadata": {"source": "3GPP_TS38.211", "topic": "NR Physical Layer Numerology", "spec": "TS 38.211", "release": "15"},
    },
    {
        "text": (
            "Network Slicing allows a single 5G physical network to host multiple isolated virtual networks (slices). "
            "Each slice is identified by an S-NSSAI (Single Network Slice Selection Assistance Information) "
            "comprising SST (Slice/Service Type) and an optional SD (Slice Differentiator). "
            "Standardised SST values: 1 = eMBB, 2 = URLLC, 3 = MIoT (Massive IoT), 4 = V2X. "
            "The NSSF (Network Slice Selection Function) selects slices at UE registration. "
            "Slices can have dedicated UPFs, SMFs, and PCFs for isolation. "
            "Maximum 8 S-NSSAIs per UE in one PLMN. Defined in TS 23.501, Section 5.15."
        ),
        "metadata": {"source": "3GPP_TS23.501_Slicing", "topic": "Network Slicing", "spec": "TS 23.501", "release": "15"},
    },
    {
        "text": (
            "VoNR (Voice over New Radio) delivers native voice over 5G Standalone networks using IMS "
            "(IP Multimedia Subsystem), defined in TS 26.114 and TS 23.228. "
            "VoNR quality of service uses 5QI=1 (GBR, 100 ms packet delay budget) for conversational voice. "
            "Codec support: EVS (Enhanced Voice Services) is mandatory; AMR-WB is also supported. "
            "EPS Fallback: when 5G coverage is insufficient, the UE falls back to LTE/VoLTE for the voice call. "
            "SRVCC (Single Radio Voice Call Continuity) enables handover of VoNR to UTRAN/GERAN. "
            "VoNR requires IMS registration over the 5G PDU session with dedicated QoS flow."
        ),
        "metadata": {"source": "3GPP_TS26.114", "topic": "Voice over NR (VoNR)", "spec": "TS 26.114", "release": "15"},
    },
    {
        "text": (
            "5G security architecture is defined in TS 33.501. "
            "Primary authentication uses 5G-AKA (Authentication and Key Agreement) or EAP-AKA' protocols. "
            "SUCI (Subscription Concealed Identifier) conceals the SUPI (permanent subscriber ID) "
            "on the air interface using ECIES (Elliptic Curve Integrated Encryption Scheme). "
            "Security keys: KAUSF → KSEAF → KAMF → KgNB (hierarchical key derivation). "
            "NAS (Non-Access Stratum) integrity protection is mandatory; NAS confidentiality is also supported. "
            "AS (Access Stratum) security provides both integrity and encryption of RRC and user-plane data. "
            "Supported algorithms: 128-bit NEA0 (null), NEA1 (SNOW 3G), NEA2 (AES-CTR), NEA3 (ZUC)."
        ),
        "metadata": {"source": "3GPP_TS33.501", "topic": "5G Security Architecture", "spec": "TS 33.501", "release": "15"},
    },
    {
        "text": (
            "Handover procedures in 5G NR are specified in TS 38.300 and TS 38.331. "
            "Types of handover: "
            "(1) Intra-gNB handover — within the same base station, no core involvement. "
            "(2) Xn-based handover — between different gNBs via the Xn interface, without AMF involvement (fast). "
            "(3) N2-based handover — involves the AMF; used for inter-AMF scenarios. "
            "(4) Conditional Handover (CHO) — UE executes handover independently upon meeting conditions, "
            "reducing interruption time at cell edges. "
            "DAPS (Dual Active Protocol Stack) handover maintains the source cell connection until the target is ready, "
            "reducing packet loss. Handover measurement events: A3, A4, A5 for intra-frequency; B1, B2 for inter-RAT."
        ),
        "metadata": {"source": "3GPP_TS38.300_HO", "topic": "5G Handover Procedures", "spec": "TS 38.300", "release": "16"},
    },
    {
        "text": (
            "HARQ (Hybrid Automatic Repeat reQuest) combines FEC (Forward Error Correction) with ARQ retransmissions "
            "to provide reliable data delivery in 5G NR. "
            "5G NR supports up to 16 HARQ processes per UE in the downlink and 16 in the uplink. "
            "Combining methods: Chase Combining (retransmit identical data) and Incremental Redundancy (IR) "
            "which transmits different parity bits each retransmission for additional coding gain. "
            "HARQ-ACK/NACK feedback is sent on PUCCH. "
            "Asynchronous HARQ is used in both UL and DL for flexibility. "
            "HARQ round-trip time (RTT) is ~8 ms in LTE, reduced to ~4 ms in 5G NR (30 kHz SCS). "
            "Defined in TS 38.212 and TS 38.213."
        ),
        "metadata": {"source": "3GPP_TS38.212", "topic": "HARQ in 5G NR", "spec": "TS 38.212", "release": "15"},
    },
    {
        "text": (
            "QoS (Quality of Service) framework in 5G is governed by 5QI (5G QoS Identifier) values defined in TS 23.501, Table 5.7.4-1. "
            "QoS flows are either GBR (Guaranteed Bit Rate) or Non-GBR. "
            "Key GBR 5QI values: 1 (Conversational Voice, 100 ms delay), 2 (Conversational Video, 150 ms), "
            "3 (Real-Time Gaming, 50 ms), 65 (Mission-Critical Push-to-Talk, 75 ms). "
            "Key Non-GBR 5QI values: 5 (IMS Signalling, 100 ms), 8 & 9 (Video TCP, 300 ms), "
            "6 (Video UDP, 300 ms). "
            "QoS parameters: 5QI, ARP (Allocation and Retention Priority), GBR/MBR/AMBR. "
            "The SMF enforces QoS policy; the UPF marks and shapes packets."
        ),
        "metadata": {"source": "3GPP_TS23.501_QoS", "topic": "5G QoS and 5QI", "spec": "TS 23.501", "release": "15"},
    },
    {
        "text": (
            "Open RAN (O-RAN) disaggregates traditional monolithic base stations into open, interoperable components. "
            "Key O-RAN elements: O-RU (Radio Unit) handles RF and lower PHY; O-DU (Distributed Unit) handles "
            "upper PHY, MAC, and RLC; O-CU (Centralised Unit) handles PDCP, SDAP, and RRC. "
            "The Open Fronthaul interface (O-RAN WG4 7.2x split) connects O-RU to O-DU. "
            "RIC (RAN Intelligent Controller): Near-RT RIC (10 ms–1 s control loop) runs xApps; "
            "Non-RT RIC (>1 s) runs rApps for policy-based optimisation. "
            "O-RAN enables multi-vendor deployments, AI/ML-driven RAN optimisation, and cost reduction. "
            "O1, O2, A1, E2 are key O-RAN interfaces."
        ),
        "metadata": {"source": "ORAN_Alliance_WG1", "topic": "Open RAN Architecture", "spec": "O-RAN.WG1", "release": "N/A"},
    },
    {
        "text": (
            "NB-IoT (Narrowband IoT), defined in 3GPP Release 13, is a Low Power Wide Area (LPWA) standard "
            "occupying 180 kHz bandwidth. Deployment modes: in-band (within LTE carrier), guard-band, standalone. "
            "Key features: up to 164 dB MCL (Maximum Coupling Loss) for deep indoor coverage; "
            "PSM (Power Saving Mode) and eDRX (Extended Discontinuous Reception) for 10+ year battery life; "
            "supports up to 50,000–200,000 devices per cell. "
            "Peak data rate: ~250 kbps DL, ~20 kbps UL. "
            "Use cases: smart meters, asset tracking, agriculture sensors, smart parking. "
            "Half-duplex FDD operation. Defined in TS 36.211 (NB-IoT physical layer)."
        ),
        "metadata": {"source": "3GPP_TS36.211_NB-IoT", "topic": "NB-IoT", "spec": "TS 36.211", "release": "13"},
    },
    {
        "text": (
            "Carrier Aggregation (CA) combines multiple component carriers (CCs) to increase throughput. "
            "In LTE: up to 5 CCs, each up to 20 MHz → 100 MHz total; defined in Release 10. "
            "In 5G NR: up to 16 CCs → up to 1 GHz total bandwidth (FR2). "
            "CA types: Intra-band contiguous (same band, adjacent carriers), "
            "Intra-band non-contiguous (same band, non-adjacent), Inter-band (different bands). "
            "The PCell (Primary Cell) provides NAS-level control and PUCCH for UL control; "
            "SCells (Secondary Cells) add capacity without dedicated control channels. "
            "SCell activation/deactivation is dynamic. CA configuration is via RRC (TS 38.331)."
        ),
        "metadata": {"source": "3GPP_TS38.331_CA", "topic": "Carrier Aggregation", "spec": "TS 38.331", "release": "15"},
    },
    {
        "text": (
            "3GPP Release History summary: "
            "Release 8 (Dec 2008) — LTE, SAE/EPC introduced. "
            "Release 9 (Dec 2009) — LTE SON, MBMS enhancements, femtocells (HeNB). "
            "Release 10 (Mar 2011) — LTE-Advanced: carrier aggregation, enhanced MIMO (8×8 DL), eICIC. "
            "Release 12 (Dec 2014) — small cells, device-to-device (ProSe), SON enhancements. "
            "Release 13 (Dec 2015) — LTE-Advanced Pro: NB-IoT, eMTC (Cat-M1), LAA, MulteFire. "
            "Release 14 (Mar 2017) — V2X, further NB-IoT enhancements. "
            "Release 15 (Jun 2018) — 5G NR Phase 1: NSA (Option 3x) and SA (Option 2), initial 5GC. "
            "Release 16 (Jul 2020) — 5G Phase 2: URLLC, V2X NR, IAB, MIMO enhancements. "
            "Release 17 (Mar 2022) — NR-Light (RedCap), NTN (satellite), sidelink relay. "
            "Release 18 (Dec 2023) — 5G-Advanced: AI/ML for RAN, XR, energy efficiency."
        ),
        "metadata": {"source": "3GPP_Release_Overview", "topic": "3GPP Release History", "spec": "Overview", "release": "All"},
    },
]


# ── Schema inspection helpers ────────────────────────────────────────────────

def inspect_schema(dataset) -> None:
    """Log the dataset schema and a sample record for debugging."""
    log.info("── Dataset Schema ──────────────────────────────")
    if hasattr(dataset, "features"):
        log.info(f"  Features: {dataset.features}")
    if hasattr(dataset, "column_names"):
        log.info(f"  Columns : {dataset.column_names}")

    sample = dataset[0]
    log.info(f"  Keys    : {list(sample.keys())}")
    for k, v in sample.items():
        snippet = str(v)[:120].replace("\n", " ") if v is not None else "None"
        log.info(f"    {k:20s}: {snippet}")
    log.info("────────────────────────────────────────────────")


def detect_text_fields(sample: Dict[str, Any]) -> List[str]:
    """Return field names that likely contain usable document text (>50 chars)."""
    priority = [
        "context", "document", "text", "content", "passage",
        "answer", "output", "response", "instruction", "input", "question",
    ]
    found = []
    for field in priority:
        val = sample.get(field)
        if val and isinstance(val, str) and len(val.strip()) > 50:
            found.append(field)

    # Also include any other long string fields not already captured
    for key, val in sample.items():
        if key not in found and isinstance(val, str) and len(val.strip()) > 50:
            found.append(key)

    return found


# ── Dataset loading ──────────────────────────────────────────────────────────

def load_tspec_dataset(sample_size: int):
    """Attempt to load TSpec-LLM from HuggingFace. Returns a list of raw records or None."""
    try:
        from datasets import load_dataset
    except ImportError:
        log.warning("'datasets' package not installed. Using mock data.")
        return None

    log.info(f"Loading dataset: {TSPEC_DATASET}")
    dataset = None

    # Try common split names in order of likelihood
    for split in ("train", "test", "validation", None):
        try:
            if split:
                dataset = load_dataset(
                    TSPEC_DATASET, split=split, trust_remote_code=True
                )
            else:
                ds_dict = load_dataset(TSPEC_DATASET, trust_remote_code=True)
                split_name = list(ds_dict.keys())[0]
                dataset = ds_dict[split_name]
            log.info(f"Loaded split '{split or split_name}': {len(dataset)} records")
            break
        except Exception as exc:
            log.debug(f"Split '{split}' failed: {exc}")

    if dataset is None:
        log.warning("Could not load any split from the dataset.")
        return None

    inspect_schema(dataset)

    # Determine the primary text field
    sample = dataset[0]
    text_fields = detect_text_fields(sample)
    if not text_fields:
        log.warning("No suitable text fields found. Using mock data.")
        return None

    primary_field = text_fields[0]
    log.info(f"Using primary text field: '{primary_field}'")

    # Build document list
    n = min(sample_size, len(dataset))
    documents: List[Dict[str, Any]] = []

    for i in range(n):
        record = dataset[i]
        text = str(record.get(primary_field, "")).strip()
        if len(text) < 30:
            continue

        # For QA datasets: optionally prepend the question for context
        if primary_field in ("answer", "output", "response"):
            q = str(record.get("question") or record.get("instruction") or "").strip()
            if q:
                text = f"Q: {q}\nA: {text}"

        metadata: Dict[str, Any] = {
            "source": f"TSpec-LLM_{i:05d}",
            "dataset": TSPEC_DATASET,
            "record_index": i,
        }
        # Copy useful metadata fields if present
        for mf in ("source", "document_id", "doc_id", "spec", "topic", "domain", "question"):
            val = record.get(mf)
            if val and isinstance(val, str):
                metadata[mf] = val[:300]

        documents.append({"text": text, "metadata": metadata})

    log.info(f"Extracted {len(documents)} valid documents from dataset")
    return documents if documents else None


# ── ChromaDB ingestion ───────────────────────────────────────────────────────

def ingest_chunks(chunks: List[Dict[str, Any]], reset: bool = False) -> int:
    """Embed chunks and store them in ChromaDB.

    Args:
        chunks: List of {"text": ..., "metadata": ...} dicts.
        reset:  If True, delete the existing collection first.

    Returns:
        Number of chunks stored.
    """
    if not chunks:
        log.error("No chunks to ingest.")
        return 0

    if reset:
        log.warning("Resetting ChromaDB collection before ingestion...")
        try:
            delete_collection(CHROMA_COLLECTION)
        except Exception:
            pass  # collection may not exist yet

    embeddings_model = get_embeddings()
    collection = get_or_create_collection(CHROMA_COLLECTION)

    BATCH = 50
    total = 0

    for start in range(0, len(chunks), BATCH):
        batch = chunks[start : start + BATCH]
        texts = [c["text"] for c in batch]
        metas = [c["metadata"] for c in batch]
        ids = [f"chunk_{start + j:06d}" for j in range(len(batch))]

        try:
            embeddings = embeddings_model.embed_documents(texts)
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metas,
                ids=ids,
            )
            total += len(batch)
            log.info(f"  Batch {start}–{start + len(batch) - 1} stored ({total} total)")
        except Exception as exc:
            log.error(f"  Batch {start} failed: {exc}")

    log.info(f"Ingestion complete — {total} chunks in ChromaDB (collection: '{CHROMA_COLLECTION}')")
    return total


# ── Main pipeline ────────────────────────────────────────────────────────────

def run_ingestion(force_mock: bool = False, reset: bool = False) -> None:
    """Full ingestion pipeline."""
    log.info("═══ Telecom Knowledge Assistant — Ingestion Pipeline ═══")

    documents: Optional[List[Dict[str, Any]]] = None

    if not force_mock:
        documents = load_tspec_dataset(TSPEC_SAMPLE_SIZE)

    if not documents:
        log.info("Using built-in mock telecom documents (15 docs covering key 3GPP topics)")
        documents = [
            {"text": d["text"], "metadata": d["metadata"]} for d in MOCK_DOCS
        ]

    # Save a preview to disk for inspection
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    preview_path = RAW_DATA_DIR / "tspec_sample.json"
    with open(preview_path, "w", encoding="utf-8") as fh:
        json.dump(documents[:20], fh, indent=2, ensure_ascii=False)
    log.info(f"Saved raw preview → {preview_path}")

    # Chunk
    log.info("Chunking documents...")
    chunks = chunk_documents(documents)
    if not chunks:
        log.error("Chunking produced no output. Aborting.")
        return

    # Save chunk preview
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    chunk_path = PROCESSED_DATA_DIR / "chunks_preview.json"
    with open(chunk_path, "w", encoding="utf-8") as fh:
        json.dump(chunks[:30], fh, indent=2, ensure_ascii=False)
    log.info(f"Saved chunk preview → {chunk_path}")

    # Ingest
    ingest_chunks(chunks, reset=reset)
    log.info("═══ Pipeline complete ═══")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest TSpec-LLM docs into ChromaDB")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Skip HuggingFace download and use built-in mock data",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing ChromaDB collection before ingesting",
    )
    args = parser.parse_args()
    run_ingestion(force_mock=args.mock, reset=args.reset)
