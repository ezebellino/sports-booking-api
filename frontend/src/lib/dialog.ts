import "sweetalert2/dist/sweetalert2.min.css";
import Swal from "sweetalert2";

const baseDialog = Swal.mixin({
  background: "#ffffff",
  color: "#0f172a",
  confirmButtonColor: "#0f172a",
  cancelButtonColor: "#e2e8f0",
  customClass: {
    popup: "rounded-[28px]",
    confirmButton: "rounded-2xl px-5 py-3 font-semibold",
    cancelButton: "rounded-2xl px-5 py-3 font-semibold text-slate-700",
  },
  buttonsStyling: true,
});

export async function confirmDestructiveAction(input: {
  title: string;
  text: string;
  confirmText: string;
}) {
  const result = await baseDialog.fire({
    icon: "warning",
    title: input.title,
    text: input.text,
    showCancelButton: true,
    confirmButtonText: input.confirmText,
    cancelButtonText: "Cancelar",
    reverseButtons: true,
    focusCancel: true,
  });

  return result.isConfirmed;
}
