"""
Боковая панель: группа настроек DXF-экспорта.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
    QMessageBox, QFileDialog,
)

from source.i18n import t
from source.ui import styles
from source.services.dxf_export import images_to_dxf


class DxfPanel(QGroupBox):
    """Группа настроек и кнопка запуска DXF-экспорта."""

    def __init__(self, parent=None):
        super().__init__(t("dxf_group"), parent)
        self.setStyleSheet(styles.group_qss())

        self._images_folder: Optional[Path] = None
        self._output_path: Optional[Path] = None
        self._thread: Optional[threading.Thread] = None

        self._build_ui()
        self._apply_i18n()

    # ---------- UI ----------
    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setSpacing(4)

        # --- images folder ---
        row = QHBoxLayout()
        self.lbl_folder = QLabel(t("dxf_folder"))
        row.addWidget(self.lbl_folder)
        self.edit_folder = QLineEdit("")
        self.edit_folder.setReadOnly(True)
        row.addWidget(self.edit_folder, 1)
        self.btn_folder = QPushButton("…")
        self.btn_folder.setFixedWidth(30)
        self.btn_folder.clicked.connect(self._choose_folder)
        row.addWidget(self.btn_folder)
        v.addLayout(row)

        # --- output file ---
        row = QHBoxLayout()
        self.lbl_output = QLabel(t("dxf_output"))
        row.addWidget(self.lbl_output)
        self.edit_output = QLineEdit("")
        self.edit_output.setReadOnly(True)
        row.addWidget(self.edit_output, 1)
        self.btn_output = QPushButton("…")
        self.btn_output.setFixedWidth(30)
        self.btn_output.clicked.connect(self._choose_output)
        row.addWidget(self.btn_output)
        v.addLayout(row)

        # --- naming + cols ---
        form = QGridLayout()
        form.setHorizontalSpacing(6)
        form.setVerticalSpacing(4)

        self.lbl_naming = QLabel(t("dxf_naming"))
        self.cmb_naming = QComboBox()
        self.cmb_naming.addItem(t("dxf_naming_auto"), "auto")
        self.cmb_naming.addItem(t("dxf_naming_coords"), "coords")
        self.cmb_naming.addItem(t("dxf_naming_seq"), "seq")
        form.addWidget(self.lbl_naming, 0, 0)
        form.addWidget(self.cmb_naming, 0, 1, 1, 2)

        self.lbl_cols = QLabel(t("dxf_cols_override"))
        self.sp_cols = QSpinBox(); self.sp_cols.setRange(0, 200); self.sp_cols.setValue(0)
        form.addWidget(self.lbl_cols, 1, 0)
        form.addWidget(self.sp_cols, 1, 1)

        self.lbl_overlap = QLabel(t("dxf_overlap_px"))
        self.sp_overlap = QSpinBox(); self.sp_overlap.setRange(0, 200); self.sp_overlap.setValue(0)
        form.addWidget(self.lbl_overlap, 2, 0)
        form.addWidget(self.sp_overlap, 2, 1)

        self.lbl_scale = QLabel(t("dxf_scale"))
        self.sp_scale = QDoubleSpinBox()
        self.sp_scale.setRange(0.0001, 100.0)
        self.sp_scale.setValue(0.01)
        self.sp_scale.setDecimals(4)
        self.sp_scale.setSingleStep(0.001)
        form.addWidget(self.lbl_scale, 3, 0)
        form.addWidget(self.sp_scale, 3, 1)

        v.addLayout(form)

        # --- contour params ---
        form2 = QGridLayout()
        form2.setHorizontalSpacing(6)
        form2.setVerticalSpacing(4)

        self.lbl_blur = QLabel(t("dxf_blur"))
        self.sp_blur = QSpinBox(); self.sp_blur.setRange(0, 31); self.sp_blur.setValue(3); self.sp_blur.setSingleStep(2)
        form2.addWidget(self.lbl_blur, 0, 0); form2.addWidget(self.sp_blur, 0, 1)

        self.lbl_canny_lo = QLabel(t("dxf_canny_low"))
        self.sp_canny_lo = QSpinBox(); self.sp_canny_lo.setRange(0, 500); self.sp_canny_lo.setValue(40)
        form2.addWidget(self.lbl_canny_lo, 1, 0); form2.addWidget(self.sp_canny_lo, 1, 1)

        self.lbl_canny_hi = QLabel(t("dxf_canny_high"))
        self.sp_canny_hi = QSpinBox(); self.sp_canny_hi.setRange(0, 500); self.sp_canny_hi.setValue(120)
        form2.addWidget(self.lbl_canny_hi, 2, 0); form2.addWidget(self.sp_canny_hi, 2, 1)

        self.lbl_min_area = QLabel(t("dxf_min_area"))
        self.sp_min_area = QDoubleSpinBox(); self.sp_min_area.setRange(0.0, 1000000.0); self.sp_min_area.setValue(30.0); self.sp_min_area.setDecimals(1)
        form2.addWidget(self.lbl_min_area, 3, 0); form2.addWidget(self.sp_min_area, 3, 1)

        self.lbl_eps = QLabel(t("dxf_approx_eps"))
        self.sp_eps = QDoubleSpinBox(); self.sp_eps.setRange(0.1, 20.0); self.sp_eps.setValue(1.5); self.sp_eps.setDecimals(2); self.sp_eps.setSingleStep(0.1)
        form2.addWidget(self.lbl_eps, 4, 0); form2.addWidget(self.sp_eps, 4, 1)

        v.addLayout(form2)

        # --- checkboxes ---
        self.chk_invert = QCheckBox(t("dxf_invert"))
        self.chk_adaptive = QCheckBox(t("dxf_adaptive"))
        self.chk_skeletonize = QCheckBox(t("dxf_skeletonize"))
        self.chk_preview = QCheckBox(t("dxf_save_preview")); self.chk_preview.setChecked(True)
        self.chk_mask = QCheckBox(t("dxf_save_mask"))
        v.addWidget(self.chk_invert)
        v.addWidget(self.chk_adaptive)
        v.addWidget(self.chk_skeletonize)
        v.addWidget(self.chk_preview)
        v.addWidget(self.chk_mask)

        # --- skeleton options (появляются при включённой скелетизации) ---
        self.skel_options = QWidget()
        skel_layout = QGridLayout(self.skel_options)
        skel_layout.setContentsMargins(0, 0, 0, 0)
        skel_layout.setHorizontalSpacing(6)
        skel_layout.setVerticalSpacing(4)

        self.lbl_skel_open = QLabel(t("dxf_skel_open"))
        self.sp_skel_open = QSpinBox()
        self.sp_skel_open.setRange(1, 15)
        self.sp_skel_open.setValue(3)
        self.sp_skel_open.setSingleStep(2)

        self.lbl_skel_prune = QLabel(t("dxf_skel_prune"))
        self.sp_skel_prune = QSpinBox()
        self.sp_skel_prune.setRange(0, 100)
        self.sp_skel_prune.setValue(8)

        skel_layout.addWidget(self.lbl_skel_open, 0, 0)
        skel_layout.addWidget(self.sp_skel_open, 0, 1)
        skel_layout.addWidget(self.lbl_skel_prune, 1, 0)
        skel_layout.addWidget(self.sp_skel_prune, 1, 1)

        v.addWidget(self.skel_options)
        self.skel_options.setVisible(False)
        self.chk_skeletonize.stateChanged.connect(
            lambda s: self.skel_options.setVisible(s == Qt.CheckState.Checked.value)
        )

        # --- buttons ---
        row = QHBoxLayout()
        self.btn_run = QPushButton(t("dxf_run"))
        self.btn_run.setStyleSheet(styles.primary_qss())
        self.btn_run.clicked.connect(self._run)
        self.btn_open = QPushButton(t("dxf_open_result"))
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self._open_result)
        row.addWidget(self.btn_run, 2)
        row.addWidget(self.btn_open, 1)
        v.addLayout(row)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color:#FFAF26;font-size:11px;")
        self.lbl_status.setWordWrap(True)
        v.addWidget(self.lbl_status)

    # ---------- i18n ----------
    def _apply_i18n(self):
        self.setTitle(t("dxf_group"))
        self.lbl_folder.setText(t("dxf_folder"))
        self.lbl_output.setText(t("dxf_output"))
        self.lbl_naming.setText(t("dxf_naming"))
        self.cmb_naming.setItemText(0, t("dxf_naming_auto"))
        self.cmb_naming.setItemText(1, t("dxf_naming_coords"))
        self.cmb_naming.setItemText(2, t("dxf_naming_seq"))
        self.lbl_cols.setText(t("dxf_cols_override"))
        self.lbl_overlap.setText(t("dxf_overlap_px"))
        self.lbl_scale.setText(t("dxf_scale"))
        self.lbl_blur.setText(t("dxf_blur"))
        self.lbl_canny_lo.setText(t("dxf_canny_low"))
        self.lbl_canny_hi.setText(t("dxf_canny_high"))
        self.lbl_min_area.setText(t("dxf_min_area"))
        self.lbl_eps.setText(t("dxf_approx_eps"))
        self.chk_invert.setText(t("dxf_invert"))
        self.chk_adaptive.setText(t("dxf_adaptive"))
        self.chk_skeletonize.setText(t("dxf_skeletonize"))
        self.chk_preview.setText(t("dxf_save_preview"))
        self.chk_mask.setText(t("dxf_save_mask"))
        if hasattr(self, "lbl_skel_open"):
            self.lbl_skel_open.setText(t("dxf_skel_open"))
            self.lbl_skel_prune.setText(t("dxf_skel_prune"))
        self.btn_run.setText(t("dxf_run"))
        self.btn_open.setText(t("dxf_open_result"))

    # ---------- handlers ----------
    def _choose_folder(self):
        start = str(self._images_folder or Path.home())
        chosen = QFileDialog.getExistingDirectory(self, t("dxf_folder"), start)
        if not chosen:
            return
        self._images_folder = Path(chosen)
        self.edit_folder.setText(str(self._images_folder))
        if not self._output_path:
            default_out = self._images_folder / "pcb.dxf"
            self._output_path = default_out
            self.edit_output.setText(str(default_out))

    def _choose_output(self):
        start = str(self._output_path or Path.home())
        chosen, _ = QFileDialog.getSaveFileName(
            self, t("dxf_output"), start, "DXF (*.dxf)")
        if not chosen:
            return
        self._output_path = Path(chosen)
        self.edit_output.setText(str(self._output_path))

    def _run(self):
        if self._thread and self._thread.is_alive():
            return
        if self._images_folder is None or not self._images_folder.exists():
            QMessageBox.warning(self, t("dxf_error"), t("dxf_need_folder"))
            return
        if self._output_path is None:
            self._output_path = self._images_folder / "pcb.dxf"
            self.edit_output.setText(str(self._output_path))

        self._set_running(True)
        self.lbl_status.setText(t("dxf_progress"))

        params = dict(
            folder=self._images_folder,
            out_dxf=self._output_path,
            naming=self.cmb_naming.currentData(),
            cols_override=int(self.sp_cols.value()) or None,
            overlap_px=int(self.sp_overlap.value()),
            blur=int(self.sp_blur.value()),
            canny_low=int(self.sp_canny_lo.value()),
            canny_high=int(self.sp_canny_hi.value()),
            min_area=float(self.sp_min_area.value()),
            approx_eps=float(self.sp_eps.value()),
            invert=bool(self.chk_invert.isChecked()),
            use_adaptive=bool(self.chk_adaptive.isChecked()),
            skeletonize=bool(self.chk_skeletonize.isChecked()),
            skel_open=int(self.sp_skel_open.value()),
            skel_prune=int(self.sp_skel_prune.value()),
            scale_mm_per_px=float(self.sp_scale.value()),
            save_preview=bool(self.chk_preview.isChecked()),
            save_mask=bool(self.chk_mask.isChecked()),
            progress_cb=lambda msg: self.lbl_status.setText(msg),
        )
        self._thread = threading.Thread(target=self._worker, kwargs=params, daemon=True)
        self._thread.start()

    def _worker(self, **params):
        try:
            stats = images_to_dxf(**params)
        except Exception as e:
            self.lbl_status.setText(f"{t('dxf_error')}: {e}")
            self._set_running(False)
            return

        skel_mark = " (skeletonized)" if stats.get("skeletonized") else ""
        text = (
            f"{t('dxf_done')}\n"
            f"  images: {stats['images']}\n"
            f"  mosaic: {stats['mosaic_shape'][0]}x{stats['mosaic_shape'][1]}\n"
            f"  contours: {stats['contours']}{skel_mark}\n"
            f"  dxf: {stats['dxf']}"
        )
        self.lbl_status.setText(text)
        self._set_running(False)
        self.btn_open.setEnabled(True)

    def _set_running(self, running: bool):
        self.btn_run.setEnabled(not running)
        self.btn_folder.setEnabled(not running)
        self.btn_output.setEnabled(not running)

    def _open_result(self):
        if self._output_path and self._output_path.exists():
            import os, sys
            from source.config import IS_WINDOWS
            p = self._output_path.parent
            try:
                if IS_WINDOWS:
                    os.startfile(str(p))  # type: ignore
                elif sys.platform == "darwin":
                    os.system(f'open "{p}"')
                else:
                    os.system(f'xdg-open "{p}"')
            except Exception as e:
                QMessageBox.warning(self, t("dxf_error"), str(e))

    def retranslate(self):
        self._apply_i18n()