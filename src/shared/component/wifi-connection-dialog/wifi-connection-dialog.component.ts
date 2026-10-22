import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-wifi-connection-dialog',
  templateUrl: './wifi-connection-dialog.component.html',
  styleUrls: ['./wifi-connection-dialog.component.scss']
})
export class WifiConnectionDialogComponent {
  status: 'connecting' | 'success' | 'failed' = 'connecting';

  constructor(
    @Inject(MAT_DIALOG_DATA) public dialogData: { ssid: string },
    public dialogRef: MatDialogRef<WifiConnectionDialogComponent>
  ) { }
}
