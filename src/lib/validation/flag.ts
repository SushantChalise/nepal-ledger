/**
 * Write a `data_quality_flag` row. Thin wrapper that fixes the shape the
 * validation driver builds (staging row id + flag type + severity + detail);
 * keeps the driver readable.
 */

import { insertDataQualityFlag } from '@/lib/db/repositories/data-quality-flags';
import type { DataQualityFlagType, FlagSeverity } from '@/lib/db/schema/enums';
import type { DataQualityFlagRow } from '@/lib/db/schema/indicator-values';
import { type Result } from '@/lib/errors';

export type FlagInput = {
  stagingRowId: string;
  flagType: DataQualityFlagType;
  severity: FlagSeverity;
  detail: string;
};

export async function writeFlag(input: FlagInput): Promise<Result<DataQualityFlagRow>> {
  return insertDataQualityFlag({
    stagingRowId: input.stagingRowId,
    flagType: input.flagType,
    severity: input.severity,
    detail: input.detail,
  });
}
