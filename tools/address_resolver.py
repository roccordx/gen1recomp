from __future__ import annotations

from analysis import (
    AddressResolution,
    RomAnalysis,
    RomNormalizedAnalysis,
    RomQualityAnalysis,
)


class AddressResolver:

    def __init__(
        self,
        analysis: RomAnalysis,
        normalized: RomNormalizedAnalysis,
        quality: RomQualityAnalysis,
    ):
        self.analysis = analysis
        self.normalized = normalized
        self.quality = quality

    def resolve(
        self,
        bank: int,
        address: int,
    ) -> AddressResolution:

        # trova la quality della bank
        quality = next(
            (
                b
                for b in self.quality.banks
                if b.bank == bank
            ),
            None,
        )

        if quality is None or not quality.ready:
            return AddressResolution(
                bank=bank,
                source_address=address,
                target_address=None,
                resolved=False,
                offset=None,
            )

        # trova i segmenti della bank
        normalized = next(
            (
                b
                for b in self.normalized.banks
                if b.bank == bank
            ),
            None,
        )

        if normalized is None:
            return AddressResolution(
                bank=bank,
                source_address=address,
                target_address=None,
                resolved=False,
                offset=None,
            )

        # cerca un segmento strutturale che contiene l'indirizzo.
        # Outlier e segmenti non strutturali non sono evidenza sufficiente
        # per risolvere automaticamente un simbolo.
        for segment in normalized.segments:

            if not segment.structural or segment.outlier:
                continue

            if segment.start <= address <= segment.end:

                return AddressResolution(
                    bank=bank,
                    source_address=address,
                    target_address=address + segment.offset,
                    resolved=True,
                    offset=segment.offset,
                )

        return AddressResolution(
            bank=bank,
            source_address=address,
            target_address=None,
            resolved=False,
            offset=None,
        )