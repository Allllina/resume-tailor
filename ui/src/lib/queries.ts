/**
 * TanStack Query hooks wrapping lib/api.ts.
 *
 * Convention:
 * - List query key: ["runs"]
 * - Detail query key: ["run", id]
 * - User status: ["userStatus"]
 * - User master tex: ["userMaster"]
 * - Tailor mutation invalidates ["runs"] and navigates to /run/<id>.
 *
 * useUserStatus uses dynamic refetchInterval to auto-poll every 5s while
 * any experience is still being scored, then stops automatically.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import {
  deleteExperience,
  deleteMaster,
  deleteUser,
  generateMaster,
  getHealth,
  getMasters,
  getPass3,
  getRun,
  getLensMasterTex,
  getUserMasterTex,
  getUserStatus,
  listRuns,
  patchRunLifecycle,
  patchUserProfile,
  postTailor,
  postVerifyClaim,
  setLensTargets,
  uploadExperiences,
  uploadResume,
  type Lens,
  type LensTargets,
  type LifecycleState,
  type LLMHealth,
  type MastersResponse,
  type Pass3Response,
  type PatchUserProfileBody,
  type RunDetail,
  type RunList,
  type TailorRequest,
  type UserStatus,
  type VerifyClaimRequest,
} from "./api";

export function useRuns() {
  return useQuery<RunList>({
    queryKey: ["runs"],
    queryFn: listRuns,
  });
}

export function useRun(id: string | undefined) {
  return useQuery<RunDetail>({
    queryKey: ["run", id],
    queryFn: () => getRun(id!),
    enabled: !!id,
  });
}

export function useTailorMutation() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (req: TailorRequest) => postTailor(req),
    onSuccess: (resp) => {
      qc.invalidateQueries({ queryKey: ["runs"] });
      navigate({ to: "/run/$id", params: { id: resp.run_id } });
    },
  });
}

// Wave 4 D.5 — Pass 3 user-trust surface
//
// usePass3 fetches the per-bullet detail for a run; safe to call on any run
// (404 just means no Pass 3 was run). useVerifyClaim records the user's
// decision and invalidates both pass3 + run + runs so the panel + Inbox
// badge update together.
export function usePass3(id: string | undefined, enabled: boolean = true) {
  return useQuery<Pass3Response>({
    queryKey: ["pass3", id],
    queryFn: () => getPass3(id!),
    enabled: !!id && enabled,
    retry: (failureCount, err) => {
      // Treat 404 as "no Pass 3 here" — don't retry. Other failures retry once.
      if ((err as { status?: number }).status === 404) return false;
      return failureCount < 1;
    },
  });
}

export function useVerifyClaim() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: VerifyClaimRequest }) =>
      postVerifyClaim(id, body),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["pass3", vars.id] });
      qc.invalidateQueries({ queryKey: ["run", vars.id] });
      qc.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}

// Wave 4 Step C — manual lifecycle transition. Invalidates both list +
// detail queries so the badge + inbox refresh together.
export function usePatchRunLifecycle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: { state: LifecycleState; note?: string; channel?: string };
    }) => patchRunLifecycle(id, body),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["runs"] });
      qc.invalidateQueries({ queryKey: ["run", vars.id] });
    },
  });
}

// --------- Wave 2.7: user / upload hooks ---------

export function useUserStatus() {
  return useQuery<UserStatus>({
    queryKey: ["userStatus"],
    queryFn: getUserStatus,
    // Poll every 5s when any experience is still scoring; stop otherwise.
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      return data.experiences_scored_count < data.experience_count ? 5000 : false;
    },
  });
}

export function useUserMasterTex(enabled: boolean) {
  return useQuery<string>({
    queryKey: ["userMaster"],
    queryFn: getUserMasterTex,
    enabled,
    staleTime: 60_000,
  });
}

export function useUploadResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadResume(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["userStatus"] });
      qc.invalidateQueries({ queryKey: ["userMaster"] });
    },
  });
}

export function useUploadExperiences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => uploadExperiences(files),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["userStatus"] });
    },
  });
}

export function useDeleteExperience() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (expId: string) => deleteExperience(expId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["userStatus"] });
    },
  });
}

export function usePatchUserProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: PatchUserProfileBody) => patchUserProfile(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["userStatus"] });
    },
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => deleteUser(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["userStatus"] });
      qc.invalidateQueries({ queryKey: ["userMaster"] });
      qc.invalidateQueries({ queryKey: ["masters"] });
    },
  });
}

// --------- C.2: per-lens master hooks ---------

/**
 * Polls /api/users/masters every 3s so the per-lens status pills (absent /
 * generating / ready) update without manual refresh during onboarding.
 *
 * The backend tracks `generating` via a filesystem sentinel that survives
 * process restarts; once cleared, the next poll flips the pill to `ready`.
 *
 * We poll continuously at 3s rather than stopping on idle so a manual
 * "Regenerate" click in /settings reflects within one window without an
 * explicit invalidate, and so an out-of-band lens-targets POST from another
 * tab still surfaces. Cost: 1 cheap GET / 3s while a Settings or Setup
 * page is open. React Query auto-stops polling when the query is unmounted.
 */
export function useMasters(enabled: boolean = true) {
  return useQuery<MastersResponse>({
    queryKey: ["masters"],
    queryFn: getMasters,
    enabled,
    refetchInterval: 3000,
  });
}

/**
 * Fetches the per-lens master.tex content. Only enabled once the inventory
 * has flipped to `ready` for that lens — `enabled` guards against 404s on
 * not-yet-generated lenses.
 */
export function useLensMasterTex(lens: Lens, enabled: boolean) {
  return useQuery<string>({
    queryKey: ["lensMaster", lens],
    queryFn: () => getLensMasterTex(lens),
    enabled,
    staleTime: 60_000,
  });
}

export function useGenerateMaster() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (lens: Lens) => generateMaster(lens),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["masters"] });
    },
  });
}

export function useDeleteMaster() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (lens: Lens) => deleteMaster(lens),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["masters"] });
      qc.invalidateQueries({ queryKey: ["userStatus"] });
    },
  });
}

export function useSetLensTargets() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: LensTargets) => setLensTargets(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["userStatus"] });
      qc.invalidateQueries({ queryKey: ["masters"] });
    },
  });
}

// Gate 2 (v0.6.2) — LLM health polling.
// Polls every 30s so the sidebar pill stays current without hammering the backend.
// Does NOT stop polling when healthy — we want continuous awareness.
// In mock mode the backend still isn't running, so errors are silenced (retry: 0).
export function useHealth() {
  return useQuery<LLMHealth>({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: 0,
    // Don't throw to error boundary — treat unreachable health endpoint as unknown state.
    throwOnError: false,
  });
}
