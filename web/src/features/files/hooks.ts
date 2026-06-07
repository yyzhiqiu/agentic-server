import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  deleteFile,
  downloadFile,
  getFiles,
  uploadFile,
} from "@/features/files/api";
import { QUERY_KEYS } from "@/shared/constants/query-keys";

export function useFiles() {
  return useQuery({
    queryKey: QUERY_KEYS.files,
    queryFn: getFiles,
  });
}

export function useUploadFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadFile,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.files,
      });
    },
  });
}

export function useDeleteFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteFile,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.files,
      });
    },
  });
}

export function useDownloadFile() {
  return useMutation({
    mutationFn: downloadFile,
  });
}
